import asyncio

from mythos_harness.config import Settings
from mythos_harness.core.triage import FrontDoorTriage, safe_json_parse
from mythos_harness.providers.local import LocalDeterministicProvider


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
