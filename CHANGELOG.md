# CHANGELOG

> Last updated: 2026-04-29  
> Automatically maintained by Cursor AI. Every change gets a concise entry.

## [Unreleased]

- 2026-04-22 – Linked local copy to `origin`, checked out `main` to match GitHub, added project knowledge docs. Rationale: sync empty local init with `myceldigital/mythos-harness` and satisfy repo hygiene (overview, learnings, changelog).
- 2026-04-22 – Bootstrapped full Mythos Harness v0.3 service scaffold (FastAPI, LangGraph orchestration, structured state, triage/branch/safety/feedback modules, tests, docs, config). Rationale: convert architecture spec into runnable repository baseline with deterministic local behavior.
- 2026-04-22 – Tightened dependency ranges and set Python floor to 3.10 for local compatibility. Rationale: avoid resolver churn/runtime mismatch while keeping architecture intact.
- 2026-04-22 – Added production adapters: OpenRouter/OpenAI-compatible provider bus, Postgres+pgvector session/trajectory stores, HTTP policy/warehouse stores, and env-driven factory wiring. Rationale: allow real API keys and external infra without code changes.
- 2026-04-22 – Replaced hash-vector session embeddings with pluggable embedding providers (local/OpenAI-compatible/OpenRouter), wired into pgvector store config. Rationale: make session memory semantics production-faithful while preserving deterministic local fallback.
- 2026-04-22 – Final hardening packet: added vector migration SQL (16->1536 safe path), similarity retrieval in session/prelude flow, API auth + rate-limit middleware, and retry/backoff wrappers for provider/store adapters. Rationale: close production-readiness gaps around safety, resilience, and memory quality.
- 2026-04-22 – Enterprise final form pass: added Redis distributed rate limiting, request-id/structured logs/Prometheus metrics, readiness probes with dependency checks, and idempotent migration runner with tracking. Rationale: make runtime operationally safe for scaled production deployment.
- 2026-04-23 – Added elite chat web UI at `/app` with persistent conversations, telemetry panels, markdown rendering, and API-key aware request flow. Rationale: deliver first-class product UX beyond raw API/docs interaction.
- 2026-04-22 – Refined `/app` into a premium operator console with redesigned visual system, status model, connection testing, tabbed insights, payload preview, and constraints/execution mode controls (without debug console clutter). Rationale: improve production usability and trust while staying aligned to real backend signals.
- 2026-04-22 – Added true progressive assistant streaming via `POST /v1/mythos/stream` (SSE events + token deltas) and updated `/app` to render tokens live with safe final replacement after safety rewrites. Rationale: remove blocking wait UX and provide real-time answer visibility without breaking existing `/complete` clients.
- 2026-04-29 – Verified Cursor Cloud dev setup with documented `just` tasks, local uvicorn startup, endpoint probes, and UI screenshot artifact. Rationale: prove the development environment is runnable and record setup evidence.

## [Past Releases]
*(Entries move here during version releases)*
