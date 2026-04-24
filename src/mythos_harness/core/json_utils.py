from __future__ import annotations

import json
import re
from typing import Any

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def extract_first_json_object(raw: str) -> str | None:
    candidates = [raw]
    candidates.extend(match.group(1) for match in _JSON_FENCE_RE.finditer(raw))

    for candidate in candidates:
        extracted = _scan_for_balanced_json_object(candidate.strip())
        if extracted is not None:
            return extracted
    return None


def safe_json_parse(raw: str, fallback: dict[str, Any]) -> dict[str, Any]:
    candidates = [raw]
    extracted = extract_first_json_object(raw)
    if extracted is not None and extracted != raw:
        candidates.append(extracted)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return fallback


def clamp_confidence(value: Any, fallback: float = 0.5) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, numeric))


def ensure_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def ensure_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def compact_text_block(lines: list[str]) -> str:
    return " ".join(line.strip() for line in lines if line.strip()).strip()


def serialize_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True)


def _scan_for_balanced_json_object(raw: str) -> str | None:
    start = raw.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(raw)):
        char = raw[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return raw[start : index + 1]

    return None


__all__ = [
    "clamp_confidence",
    "compact_text_block",
    "ensure_dict_list",
    "ensure_string_list",
    "extract_first_json_object",
    "safe_json_parse",
    "serialize_json",
]
