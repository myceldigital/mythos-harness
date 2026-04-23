# Mythos Harness Architecture Mapping

This document maps the v0.3 design to concrete implementation modules.

## Request Path

1. `POST /v1/mythos/complete` hits `mythos_harness.api.router`.
2. Router calls `MythosOrchestrator.complete`.
3. Orchestrator runs LangGraph assembled in `mythos_harness.graph.builder`.
4. Graph executes:
   - front-door triage
   - prelude state initialization
   - phase-keyed loop
   - coda synthesis
   - safety gate
   - feedback logging

Interactive usage path:

1. User opens `/app` (served from `mythos_harness.web` assets).
2. Browser UI (`app.js`) sends requests to `/v1/mythos/complete`.
3. UI renders final answer + telemetry (`loops`, `halt_reason`, `confidence`, `triage`).

## Component-to-Module Mapping

- Structured state: `mythos_harness.core.state`
- Branch manager: `mythos_harness.core.branch_manager`
- Front-door triage: `mythos_harness.core.triage`
- Phase loop: `mythos_harness.core.loop`
- Coda: `mythos_harness.core.coda`
- Safety gate: `mythos_harness.core.safety`
- Feedback logger: `mythos_harness.core.feedback`
- API hardening middleware: `mythos_harness.api.middleware`
- Observability middleware: `mythos_harness.api.observability`
- Chat UI assets: `mythos_harness.web`
- Policy store: `mythos_harness.storage.policy`
- Session store: `mythos_harness.storage.session`
- Trajectory store: `mythos_harness.storage.trajectory`
- Provider abstraction + adapters:
  - `mythos_harness.providers.base`
  - `mythos_harness.providers.local`
  - `mythos_harness.providers.openai_compatible`
  - `mythos_harness.providers.routed`
  - `mythos_harness.providers.factory`
- Storage adapter factory:
  - `mythos_harness.storage.factory`
  - `mythos_harness.storage.contracts`
- Retry utility:
  - `mythos_harness.utils.retry`
- Migration runner:
  - `scripts/apply_migrations.py`
- Embedding adapter factory:
  - `mythos_harness.embeddings.factory`
  - `mythos_harness.embeddings.local`
  - `mythos_harness.embeddings.openai_compatible`

## Runtime Backend Selection

- Provider backend is selected by `MYTHOS_PROVIDER_BACKEND`:
  - `local` (deterministic fallback)
  - `openai_compatible`
  - `openrouter`
- Optional judge-family override is controlled by `MYTHOS_JUDGE_PROVIDER_BACKEND`.
- Embedding backend for pgvector snapshots is selected by `MYTHOS_EMBEDDING_BACKEND`:
  - `local`
  - `openai_compatible`
  - `openrouter`
- API perimeter controls:
  - `MYTHOS_API_AUTH_ENABLED`, `MYTHOS_API_AUTH_KEYS`, `MYTHOS_API_AUTH_KEY_HASHES`
  - `MYTHOS_RATE_LIMIT_ENABLED`, `MYTHOS_RATE_LIMIT_REQUESTS`, `MYTHOS_RATE_LIMIT_WINDOW_S`, `MYTHOS_RATE_LIMIT_KEY_SOURCE`
  - `MYTHOS_RATE_LIMIT_BACKEND`, `MYTHOS_RATE_LIMIT_FAIL_OPEN`
  - `MYTHOS_REDIS_URL`, `MYTHOS_REDIS_PREFIX`
- Observability controls:
  - `MYTHOS_METRICS_ENABLED`, `MYTHOS_ACCESS_LOG_ENABLED`, `MYTHOS_REQUEST_ID_HEADER`, `MYTHOS_LOG_LEVEL`
- Retry controls:
  - `MYTHOS_RETRY_MAX_ATTEMPTS`, `MYTHOS_RETRY_BASE_DELAY_S`, `MYTHOS_RETRY_MAX_DELAY_S`, `MYTHOS_RETRY_JITTER_S`
- Store backends are selected independently:
  - `MYTHOS_SESSION_STORE_BACKEND` -> `memory | postgres`
  - `MYTHOS_POLICY_STORE_BACKEND` -> `file | http`
  - `MYTHOS_TRAJECTORY_STORE_BACKEND` -> `jsonl | postgres | http`

## Production Notes

- Postgres adapters auto-initialize schema/tables and require pgvector extension.
- Keep `MYTHOS_PGVECTOR_DIMENSIONS` aligned with the selected embedding model output size.
- SQL bootstrap is provided at `sql/bootstrap_postgres.sql`.
- Legacy installs can migrate vector dimensions via `sql/migrations/20260422_vector_16_to_1536.sql`.
- Enterprise migration application is available via `scripts/apply_migrations.py` / `just migrate`.
- Feedback optimization remains offline, gated, and human-approved.
