from mythos_harness.config import Settings
from mythos_harness.core.service import MythosOrchestrator
from mythos_harness.providers.factory import build_provider
from mythos_harness.storage.factory import build_storage


def test_branch_model_comes_from_settings() -> None:
    settings = Settings(_env_file=None, provider_backend="local", model_branch_alt="branch-custom")
    provider = build_provider(settings)
    stores = build_storage(settings)
    orchestrator = MythosOrchestrator(
        settings=settings,
        provider=provider,
        session_store=stores.sessions,
        policy_store=stores.policy,
        trajectory_store=stores.trajectories,
    )
    assert orchestrator.branch_manager.branch_model == "branch-custom"
