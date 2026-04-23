# Project Learnings

> Last updated: 2026-04-22

## Architectural Decisions
- [2026-04-22] – Local `Desktop/mythos harness` aligned to GitHub `myceldigital/mythos-harness`  
  **Rationale:** Local folder was an empty `git init` with no commits; the canonical history lives on `origin`.  
  **Alternatives considered:** None needed—fetch/checkout was sufficient.  
  **Impact:** `main` tracks `origin/main`; use normal pull/push for ongoing sync.
- [2026-04-22] – Implemented Mythos v0.3 as a production-shaped FastAPI + LangGraph scaffold  
  **Rationale:** v0.3 introduces front-door triage, structured latent state, branch management, and governed feedback as core architecture rather than optional extras.  
  **Alternatives considered:** Single-file or ad hoc orchestration was rejected because it obscures phase behavior and blocks safe extension.  
  **Impact:** Clear module boundaries now mirror architectural components and support swap-in production adapters.
- [2026-04-22] – Chosen env-driven adapter factories for providers and stores  
  **Rationale:** deployment environments should switch backends via configuration, not code forks.  
  **Alternatives considered:** hard-wired adapters in `main.py` were rejected as brittle.  
  **Impact:** `build_provider()` + `build_storage()` now control runtime composition.
- [2026-04-22] – pgvector session memory now uses pluggable embedding providers  
  **Rationale:** hash-based pseudo-embeddings are not production-faithful for retrieval semantics.  
  **Alternatives considered:** keeping hash vectors was rejected because they do not encode semantic similarity.  
  **Impact:** Postgres session snapshots consume real embeddings when configured, with local deterministic fallback retained.
- [2026-04-22] – Added defensive 16->1536 pgvector migration path  
  **Rationale:** existing installs may already have `vector(16)` schema from earlier scaffold versions.  
  **Alternatives considered:** direct `ALTER TYPE` was rejected as unsafe for mismatched vector dimensions.  
  **Impact:** migration preserves snapshot JSON, keeps legacy column for rollback, and enables safe re-embedding.
- [2026-04-22] – Added operational migration runner with checksum tracking  
  **Rationale:** enterprise environments need repeatable, auditable migration application.  
  **Alternatives considered:** manual `psql` sequencing was rejected as error-prone at scale.  
  **Impact:** `scripts/apply_migrations.py` now applies pending SQL files idempotently and detects drift.
- [2026-04-23] – Added first-class web chat client served by FastAPI  
  **Rationale:** docs/API-only interaction limits adoption and product feel.  
  **Alternatives considered:** separate frontend repo was deferred to avoid deployment complexity in early OSS phases.  
  **Impact:** `/app` now provides production-grade operator UX directly from the same service artifact.
- [2026-04-22] – UI refinement follows “backend-grounded premium UX” rule  
  **Rationale:** visual richness should reflect only data the API actually exposes, avoiding misleading debug theater.  
  **Alternatives considered:** importing full reference UI features (branch economy/governor diagnostics) was rejected because those signals are not emitted by current endpoint responses.  
  **Impact:** upgraded `/app` keeps premium interaction quality while remaining truthful and maintainable.
- [2026-04-22] – Streaming architecture uses additive endpoint (`/v1/mythos/stream`) rather than mutating `/complete`  
  **Rationale:** preserve backward compatibility for existing clients while enabling progressive UX in the web app.  
  **Alternatives considered:** replacing `/complete` with streaming was rejected because many integrations expect a single JSON response body.  
  **Impact:** both blocking and streaming consumers are supported without forked business logic.

## Patterns & Conventions Established
- [2026-04-22] – Phase-keyed loop as first-class runtime state  
  **When to use:** Any iterative reasoning request where we need explicit explore/solve/verify/repair/synthesize control.  
  **Example:** `MythosState.phase` is advanced by `PhaseLoop.run_current_phase()`, with halting handled by deterministic thresholds.
- [2026-04-22] – Provider abstraction with deterministic local fallback  
  **When to use:** Local development/testing without binding to paid model APIs.  
  **Example:** `LocalDeterministicProvider` returns predictable triage/judge/style outputs for repeatable tests.
- [2026-04-22] – Role-routed provider bus for external judge family  
  **When to use:** Keep judge model on a different provider family while sharing one orchestrator contract.  
  **Example:** `RoleRoutedProvider` routes `model_judge` calls to optional judge backend.
- [2026-04-22] – Embedding backend split from completion backend  
  **When to use:** Embedding APIs or models differ from chat completion providers/models.  
  **Example:** `MYTHOS_EMBEDDING_BACKEND=openai_compatible` while `MYTHOS_PROVIDER_BACKEND=openrouter`.
- [2026-04-22] – API perimeter hardening middleware  
  **When to use:** Exposed deployments that require API key auth and request throttling.  
  **Example:** `ApiKeyAuthMiddleware` + `RateLimitMiddleware` enabled through `MYTHOS_API_AUTH_*` and `MYTHOS_RATE_LIMIT_*`.
- [2026-04-22] – Distributed rate limit backend via Redis  
  **When to use:** Multi-instance deployments where in-memory throttling is insufficient.  
  **Example:** `MYTHOS_RATE_LIMIT_BACKEND=redis` with `MYTHOS_REDIS_URL` for shared quotas.
- [2026-04-22] – Request correlation and observability middleware stack  
  **When to use:** Production services requiring traceability and scrapeable SLI metrics.  
  **Example:** `RequestIdMiddleware`, `AccessLogMiddleware`, `MetricsMiddleware`, and `/metrics`.
- [2026-04-23] – Local-persistent session UX pattern in browser  
  **When to use:** Multi-turn orchestration testing without backend-side user account/session model.  
  **Example:** UI stores conversation state + endpoint/auth settings in localStorage and maps each conversation to a `thread_id`.
- [2026-04-22] – Request-shaping controls via constraints JSON + execution mode hint  
  **When to use:** Need per-run steering without changing backend code or environment config.  
  **Example:** UI emits `constraints` from JSON editor and injects `execution_mode_hint` when selected.
- [2026-04-22] – SSE over `fetch` for authenticated POST streaming  
  **When to use:** Need token streaming with custom headers/body (`x-api-key`, JSON payload) where native `EventSource` is too limited.  
  **Example:** frontend `streamCompletion()` calls `/v1/mythos/stream` via `fetch` and parses SSE frames from `ReadableStream`.

## Gotchas & Solutions
- [2026-04-22] – Empty local git dir vs populated remote  
  **Root cause:** `git init` without remote doesn’t have commits; remote already had `main`.  
  **Solution:** `git remote add origin …`, `git fetch`, `git checkout -B main origin/main`.  
  **Code snippet:** N/A (git workflow)
- [2026-04-22] – Python runtime mismatch (`datetime.UTC` unavailable in 3.10)  
  **Root cause:** Initial implementation assumed Python 3.11+ semantics.  
  **Solution:** Switched to `datetime.now(timezone.utc)` for compatibility.  
  **Code snippet:** `datetime.now(timezone.utc).isoformat()`
- [2026-04-22] – External adapter flakiness without retries  
  **Root cause:** Network/provider transient failures can spike under load.  
  **Solution:** Added centralized async retry/backoff utility and applied to HTTP + Postgres adapters.  
  **Code snippet:** `retry_async(operation, config=RetryConfig(...), retry_if=...)`
- [2026-04-22] – Rate limiter backend initialization can fail when Redis URL missing  
  **Root cause:** Backend selection evaluated before `enabled` guard.  
  **Solution:** Build Redis limiter only when rate limiting is enabled; otherwise default to in-memory no-op path.  
  **Code snippet:** `if enabled: self._limiter = self._build_limiter(...) else: InMemoryRateLimiter()`
- [2026-04-22] – Payload preview can silently drift if request state is not persisted before send  
  **Root cause:** UI settings edited in inputs but not synchronized into in-memory state before constructing request payload.  
  **Solution:** Sync settings from form inputs at submit-time and connection-test-time before serialization.  
  **Code snippet:** `syncSettingsFromInputs(); const constraints = parseConstraints();`
- [2026-04-22] – Safety revision can invalidate already-streamed coda tokens  
  **Root cause:** final post-coda safety gate may rewrite `final_answer` after stream emission starts.  
  **Solution:** emit streaming `replace` event after safety when answer changed, and let UI replace in-flight content atomically.  
  **Code snippet:** `if runtime.final_answer != streamed_answer: yield ("replace", {"text": runtime.final_answer})`

## Tech Stack / Tooling Nuances
- [2026-04-22] – LangGraph dependency can trigger resolver churn without upper bounds  
  **Key insight:** Constraining compatible ranges reduces pip backtracking significantly on Python 3.10.  
  **Best practice:** Keep bounded constraints for `fastapi`, `pydantic`, `pydantic-settings`, and `langgraph` in this repo.
- [2026-04-22] – `asyncpg` works cleanly for async Postgres/pgvector adapters  
  **Key insight:** Store adapters can remain fully async and self-initialize schema/table setup.  
  **Best practice:** keep Postgres DSN/config centralized in env and bootstrap with `sql/bootstrap_postgres.sql`.

## Performance & Optimization Notes
- *(empty)*

## Team / Workflow Agreements
- [2026-04-22] – Safety stays post-coda; feedback optimization remains offline and gated  
  **Rationale:** Keeps reasoning quality independent from decode-time safety and avoids uncontrolled prompt drift.  
  **Impact:** Trajectory logging is enabled in runtime; optimization hooks remain non-hot-path by design.
