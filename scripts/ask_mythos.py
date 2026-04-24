#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HERMES_ENV = Path.home() / ".hermes" / ".env"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _read_query(args: argparse.Namespace) -> str:
    if args.query:
        return args.query
    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            return data
    raise SystemExit("Provide a prompt as an argument or via stdin.")


def _configure_env() -> None:
    os.chdir(ROOT)
    _load_env_file(HERMES_ENV)

    if not os.getenv("MYTHOS_PROVIDER_BACKEND"):
        os.environ["MYTHOS_PROVIDER_BACKEND"] = (
            "openrouter" if os.getenv("OPENROUTER_API_KEY") else "local"
        )

    backend = os.getenv("MYTHOS_PROVIDER_BACKEND", "local")

    if backend == "openrouter" and not os.getenv("MYTHOS_PROVIDER_API_KEY"):
        if os.getenv("OPENROUTER_API_KEY"):
            os.environ["MYTHOS_PROVIDER_API_KEY"] = os.environ["OPENROUTER_API_KEY"]

    if backend == "openrouter":
        for key in (
            "MYTHOS_MODEL_BASE",
            "MYTHOS_MODEL_FAST",
            "MYTHOS_MODEL_JUDGE",
            "MYTHOS_MODEL_CODE_MATH",
            "MYTHOS_MODEL_STYLE",
            "MYTHOS_MODEL_BRANCH_ALT",
        ):
            os.environ.setdefault(key, DEFAULT_OPENROUTER_MODEL)
        os.environ.setdefault("MYTHOS_OPENROUTER_APP_NAME", "hermes-mythos")
        os.environ.setdefault("MYTHOS_OPENROUTER_SITE_URL", "https://github.com/myceldigital/mythos-harness")

    os.environ.setdefault("MYTHOS_POLICY_PATH", str(ROOT / "config" / "policy_rules.json"))
    os.environ.setdefault("MYTHOS_TRAJECTORY_STORE_PATH", str(ROOT / "data" / "trajectories.jsonl"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query the local Mythos harness")
    parser.add_argument("query", nargs="?", help="Prompt to send to Mythos. If omitted, stdin is used.")
    parser.add_argument("--thread-id", default=None, help="Optional thread/session ID.")
    parser.add_argument("--constraints", default="{}", help="JSON object of constraints to pass through.")
    parser.add_argument("--json", action="store_true", help="Print full JSON response.")
    parser.add_argument("--meta", action="store_true", help="Print answer plus metadata.")
    return parser


async def _run(query: str, thread_id: str, constraints: dict[str, Any], emit_json: bool, emit_meta: bool) -> int:
    from mythos_harness.config import get_settings
    from mythos_harness.core.service import MythosOrchestrator
    from mythos_harness.providers.factory import build_provider
    from mythos_harness.storage.factory import build_storage

    get_settings.cache_clear()
    settings = get_settings()
    provider = build_provider(settings)
    stores = build_storage(settings)
    orchestrator = MythosOrchestrator(
        settings=settings,
        provider=provider,
        session_store=stores.sessions,
        policy_store=stores.policy,
        trajectory_store=stores.trajectories,
    )

    result = await orchestrator.complete(
        query=query,
        thread_id=thread_id,
        constraints=constraints,
    )
    payload = {
        "thread_id": result.thread_id,
        "final_answer": result.final_answer,
        "confidence_summary": result.confidence_summary,
        "citations": result.citations,
        "loops": result.loop_index,
        "halt_reason": result.halt_reason,
        "trajectory_id": result.trajectory_id,
        "triage": result.triage,
    }

    if emit_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(payload["final_answer"])
        if emit_meta:
            meta = {
                "thread_id": payload["thread_id"],
                "loops": payload["loops"],
                "halt_reason": payload["halt_reason"],
                "triage": payload["triage"],
                "trajectory_id": payload["trajectory_id"],
            }
            print("\n--- META ---")
            print(json.dumps(meta, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    query = _read_query(args)
    _configure_env()

    try:
        constraints = json.loads(args.constraints)
        if not isinstance(constraints, dict):
            raise ValueError("constraints must decode to a JSON object")
    except Exception as exc:
        raise SystemExit(f"Invalid --constraints JSON: {exc}")

    thread_id = args.thread_id or f"hermes-mythos-{int(time.time())}"
    return asyncio.run(_run(query, thread_id, constraints, args.json, args.meta))


if __name__ == "__main__":
    raise SystemExit(main())
