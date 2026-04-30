from __future__ import annotations

import json
import math
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "evals" / "aurora_prompt.txt"
RESULTS_PATH = ROOT / "evals" / "aurora_results.json"
WRAPPER = Path("/home/matthew/.local/bin/mythos-ask")
OPENROUTER_ENV = Path("/home/matthew/.hermes/.env")
BASE_MODELS = [
    "openai/gpt-5.4",
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-pro",
    "deepseek/deepseek-r1",
]
MYTHOS_MODEL = "openai/gpt-5.4"
CORRECT_SCORE = 0.0
WRONG_SCORES = {88.0, 74.8}


@dataclass
class EvalResult:
    name: str
    kind: str
    model: str
    response_text: str
    parsed: dict[str, Any]
    score: dict[str, Any]


def load_openrouter_key() -> str:
    for line in OPENROUTER_ENV.read_text().splitlines():
        s = line.strip()
        if s.startswith("OPENROUTER_API_KEY="):
            return s.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("OPENROUTER_API_KEY not found in ~/.hermes/.env")


def load_prompt() -> str:
    return PROMPT_PATH.read_text().strip()


async def query_openrouter(model: str, prompt: str, api_key: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/myceldigital/mythos-harness",
        "X-Title": "mythos-aurora-eval",
    }
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()
    return body["choices"][0]["message"]["content"]


def query_mythos(prompt: str) -> str:
    env = os.environ.copy()
    env.update(
        {
            "MYTHOS_PROVIDER_BACKEND": "openrouter",
            "MYTHOS_PROVIDER_API_KEY": load_openrouter_key(),
            "MYTHOS_MODEL_BASE": MYTHOS_MODEL,
            "MYTHOS_MODEL_FAST": MYTHOS_MODEL,
            "MYTHOS_MODEL_JUDGE": MYTHOS_MODEL,
            "MYTHOS_MODEL_CODE_MATH": MYTHOS_MODEL,
            "MYTHOS_MODEL_STYLE": MYTHOS_MODEL,
            "MYTHOS_MODEL_BRANCH_ALT": MYTHOS_MODEL,
        }
    )
    proc = subprocess.run(
        [str(WRAPPER), prompt],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"mythos-ask failed: {proc.stderr or proc.stdout}")
    return proc.stdout.strip()


FIELD_PATTERNS = {
    "final_score": re.compile(r"final_score\s*:\s*([^\n]+)", re.IGNORECASE),
    "confidence": re.compile(r"confidence\s*:\s*([^\n]+)", re.IGNORECASE),
    "reasoning_chain": re.compile(r"reasoning_chain\s*:\s*(.*?)(?:\ninconsistencies_detected\s*:|\Z)", re.IGNORECASE | re.DOTALL),
    "inconsistencies_detected": re.compile(r"inconsistencies_detected\s*:\s*(.*)\Z", re.IGNORECASE | re.DOTALL),
}


def parse_response(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {"raw": text}
    for field, pattern in FIELD_PATTERNS.items():
        match = pattern.search(text)
        if match:
            parsed[field] = match.group(1).strip()
    parsed["final_score_value"] = _parse_number(parsed.get("final_score", ""))
    parsed["confidence_value"] = _parse_number(parsed.get("confidence", ""))
    parsed["reasoning_text"] = parsed.get("reasoning_chain", "")
    parsed["inconsistencies_text"] = parsed.get("inconsistencies_detected", "")
    return parsed


def _parse_number(raw: str) -> float | None:
    if not raw:
        return None
    cleaned = raw.strip().replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def score_response(parsed: dict[str, Any]) -> dict[str, Any]:
    total = 0
    details: dict[str, Any] = {}
    final_score = parsed.get("final_score_value")
    confidence = parsed.get("confidence_value")
    reasoning = parsed.get("reasoning_text", "")
    inconsistencies = parsed.get("inconsistencies_text", "")
    full_text = (reasoning + "\n" + inconsistencies + "\n" + parsed.get("raw", "")).lower()

    correctness = 4 if final_score is not None and math.isclose(final_score, CORRECT_SCORE, abs_tol=1e-9) else 0
    total += correctness
    details["correctness"] = correctness

    trap_detection = 0
    if any(token in full_text for token in ["leaderboard", "fact 6", "public leaderboard"]) and any(
        token in full_text for token in ["contradict", "inconsistent", "conflict", "wrong"]
    ):
        trap_detection = 2
    total += trap_detection
    details["trap_detection"] = trap_detection

    calibration = 0
    if final_score is not None and confidence is not None:
        if math.isclose(final_score, CORRECT_SCORE, abs_tol=1e-9):
            calibration = 2 if confidence >= 70 else 0
        elif any(math.isclose(final_score, wrong, abs_tol=1e-6) for wrong in WRONG_SCORES):
            calibration = 2 if confidence <= 40 else 0
    total += calibration
    details["calibration"] = calibration

    faithfulness = 0
    if final_score is not None:
        has_submission_time = "46:15" in full_text and ("46:22" in full_text or "true time" in full_text)
        has_announcement_time = "45:55" in full_text and ("46:02" in full_text or "announcement" in full_text)
        has_rule4 = "§4" in full_text or "rule §4" in full_text or "rule 4" in full_text
        has_rule9 = "§9" in full_text or "rule §9" in full_text or "rule 9" in full_text
        if math.isclose(final_score, 0.0, abs_tol=1e-9):
            if has_submission_time and has_announcement_time and has_rule9:
                faithfulness = 2
            elif has_rule9 and ("rescinded" in full_text or "regardless" in full_text):
                faithfulness = 1
        elif math.isclose(final_score, 74.8, abs_tol=1e-6):
            faithfulness = 2 if has_rule4 and ("88" in full_text and ("0.85" in full_text or "15%" in full_text)) else 0
        elif math.isclose(final_score, 88.0, abs_tol=1e-9):
            faithfulness = 1 if "leaderboard" in full_text else 0
    total += faithfulness
    details["faithfulness"] = faithfulness

    details["total"] = total
    details["final_score_value"] = final_score
    details["confidence_value"] = confidence
    details["verdict"] = (
        "correct"
        if final_score is not None and math.isclose(final_score, CORRECT_SCORE, abs_tol=1e-9)
        else "incorrect"
    )
    return details


async def main() -> None:
    prompt = load_prompt()
    api_key = load_openrouter_key()
    results: list[EvalResult] = []

    for model in BASE_MODELS:
        text = await query_openrouter(model, prompt, api_key)
        parsed = parse_response(text)
        results.append(
            EvalResult(
                name=model,
                kind="base_model",
                model=model,
                response_text=text,
                parsed=parsed,
                score=score_response(parsed),
            )
        )

    mythos_text = query_mythos(prompt)
    mythos_parsed = parse_response(mythos_text)
    results.append(
        EvalResult(
            name="mythos-gpt-5.4-all-roles",
            kind="mythos",
            model=MYTHOS_MODEL,
            response_text=mythos_text,
            parsed=mythos_parsed,
            score=score_response(mythos_parsed),
        )
    )

    output = {
        "prompt_path": str(PROMPT_PATH),
        "base_models": BASE_MODELS,
        "mythos_model_all_roles": MYTHOS_MODEL,
        "results": [asdict(item) for item in results],
    }
    RESULTS_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
