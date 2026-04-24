import asyncio

from mythos_harness.config import Settings
from mythos_harness.core.json_utils import extract_first_json_object
from mythos_harness.core.triage import FrontDoorTriage, safe_json_parse
from mythos_harness.providers.local import LocalDeterministicProvider


def test_extract_first_json_object_handles_fenced_payload() -> None:
    raw = "Here you go:\n```json\n{\"execution_mode\": \"deep\", \"needs_tools\": true}\n```"
    assert extract_first_json_object(raw) == '{"execution_mode": "deep", "needs_tools": true}'


def test_safe_json_parse_reads_fenced_json_payload() -> None:
    fallback = {"execution_mode": "normal"}
    raw = "```json\n{\"execution_mode\": \"deep\", \"difficulty\": 0.8}\n```"
    assert safe_json_parse(raw, fallback) == {"execution_mode": "deep", "difficulty": 0.8}


def test_safe_json_parse_uses_fallback_on_invalid_payload() -> None:
    fallback = {"execution_mode": "normal"}
    assert safe_json_parse("not-json", fallback) == fallback


def test_frontdoor_triage_returns_expected_keys() -> None:
    triage = FrontDoorTriage()
    provider = LocalDeterministicProvider()
    settings = Settings()
    result = asyncio.run(triage.triage("Complex code migration request", provider, settings))
    assert "task_type" in result
    assert "execution_mode" in result
