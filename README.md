# Mythos Harness v0.3

Mythos Harness is a FastAPI + LangGraph orchestration runtime that implements the v0.3 architecture:

- Front-door triage before deep reasoning
- Structured latent state instead of opaque hidden strings
- Branch manager for competing hypotheses
- Phase-keyed loop (`explore -> solve -> verify -> repair -> synthesize`)
- Five-model abstraction bus (base, fast, judge, code/math, style)
- Post-coda safety gate
- Passive feedback loop with governance-safe boundaries

## Repo Layout

```text
src/mythos_harness/
  api/              # FastAPI route + request/response schemas
  core/             # State model, triage, loop phases, coda, safety, feedback
  embeddings/       # Embedding provider adapters for pgvector session memory
  graph/            # LangGraph assembly and execution
  providers/        # Model provider abstraction + local deterministic provider
  storage/          # Session snapshots, trajectory logs, policy store
  main.py           # App entrypoint
tests/              # Unit + route smoke tests
mythosv3_architecture.md
```

## Quickstart

1) Create a Python 3.10+ environment.

2) Install deps:

```bash
just install
```

3) Run service:

```bash
just run
```

4) Open the chat UI:

```bash
open http://localhost:8080/app
```

5) Call endpoint directly (optional):

```bash
curl -X POST http://localhost:8080/v1/mythos/complete \
  -H "content-type: application/json" \
  -d '{"query":"Give me a migration plan from v0.2 to v0.3","thread_id":"demo-1"}'
```

## Real Provider Setup

### OpenRouter (recommended multi-model path)

```bash
export MYTHOS_PROVIDER_BACKEND=openrouter
export MYTHOS_PROVIDER_API_KEY=<your_openrouter_key>
export MYTHOS_MODEL_BASE=anthropic/claude-3.5-sonnet
export MYTHOS_MODEL_FAST=anthropic/claude-3.5-haiku
export MYTHOS_MODEL_JUDGE=openai/gpt-4o-mini
```

### Any OpenAI-compatible provider

```bash
export MYTHOS_PROVIDER_BACKEND=openai_compatible
export MYTHOS_PROVIDER_API_KEY=<your_provider_key>
export MYTHOS_PROVIDER_BASE_URL=https://api.openai.com/v1
```

### Optional separate judge backend/family

```bash
export MYTHOS_JUDGE_PROVIDER_BACKEND=openrouter
export MYTHOS_JUDGE_PROVIDER_API_KEY=<judge_key>
```

## Externalized Stores

### Postgres + pgvector for sessions/trajectories

1) Run the bootstrap SQL:

```bash
psql "$MYTHOS_POSTGRES_DSN" -f sql/bootstrap_postgres.sql
```

If you previously used `VECTOR(16)` in `mythos.session_snapshots`, run:

```bash
psql "$MYTHOS_POSTGRES_DSN" -f sql/migrations/20260422_vector_16_to_1536.sql
```

For full migration management (idempotent tracking table):

```bash
just migrate
```

2) Set store backends:

```bash
export MYTHOS_POSTGRES_DSN=postgresql://user:pass@localhost:5432/mythos
export MYTHOS_SESSION_STORE_BACKEND=postgres
export MYTHOS_TRAJECTORY_STORE_BACKEND=postgres
```

3) Configure embedding backend for pgvector vectors:

```bash
# local deterministic embeddings (offline fallback)
export MYTHOS_EMBEDDING_BACKEND=local
export MYTHOS_PGVECTOR_DIMENSIONS=1536

# or real embedding API (recommended in production)
export MYTHOS_EMBEDDING_BACKEND=openai_compatible
export MYTHOS_EMBEDDING_MODEL=text-embedding-3-small
export MYTHOS_EMBEDDING_API_KEY=<embedding_key>
# optional if your embeddings endpoint differs from model endpoint:
export MYTHOS_EMBEDDING_BASE_URL=https://api.openai.com/v1
```

### Vector similarity retrieval behavior

- At request start, the orchestrator performs similarity lookup over session snapshots.
- Retrieved memories are injected as grounded facts during prelude.
- Control top-k via `MYTHOS_MEMORY_RETRIEVAL_K` (default `3`).

### Remote policy DB

```bash
export MYTHOS_POLICY_STORE_BACKEND=http
export MYTHOS_POLICY_HTTP_URL=https://policy.example.com/v1/mythos/policy
export MYTHOS_POLICY_HTTP_API_KEY=<policy_api_key>
```

### Remote trajectory warehouse endpoint

```bash
export MYTHOS_TRAJECTORY_STORE_BACKEND=http
export MYTHOS_TRAJECTORY_HTTP_URL=https://warehouse.example.com/v1/trajectories
export MYTHOS_TRAJECTORY_HTTP_API_KEY=<warehouse_api_key>
```

## Security + Resilience Hardening

### API key auth middleware

```bash
export MYTHOS_API_AUTH_ENABLED=true
export MYTHOS_API_AUTH_KEYS=key_one,key_two
```

Clients can use either `x-api-key` or `Authorization: Bearer <key>`.

For enterprise secret hygiene, you can store SHA256 hashes instead of plaintext keys:

```bash
# comma-separated lowercase sha256 digests of valid keys
export MYTHOS_API_AUTH_KEY_HASHES=<sha256hex>,<sha256hex>
```

### Rate limit middleware

```bash
export MYTHOS_RATE_LIMIT_ENABLED=true
export MYTHOS_RATE_LIMIT_REQUESTS=60
export MYTHOS_RATE_LIMIT_WINDOW_S=60
export MYTHOS_RATE_LIMIT_KEY_SOURCE=api_key
export MYTHOS_RATE_LIMIT_BACKEND=redis
export MYTHOS_REDIS_URL=redis://localhost:6379/0
export MYTHOS_REDIS_PREFIX=mythos
export MYTHOS_RATE_LIMIT_FAIL_OPEN=false
```

### Retry/backoff for external adapters

```bash
export MYTHOS_RETRY_MAX_ATTEMPTS=3
export MYTHOS_RETRY_BASE_DELAY_S=0.25
export MYTHOS_RETRY_MAX_DELAY_S=2.0
export MYTHOS_RETRY_JITTER_S=0.05
```

## Observability + Readiness

- `GET /healthz` for liveness.
- `GET /readyz` for dependency readiness (session/policy/trajectory backends).
- `GET /metrics` Prometheus metrics endpoint.
- Request correlation IDs are attached via `x-request-id` (configurable by `MYTHOS_REQUEST_ID_HEADER`).
- Structured access logs are enabled with `MYTHOS_ACCESS_LOG_ENABLED=true`.

## API

- `POST /v1/mythos/complete`
  - Input: query, optional thread id, optional constraints.
  - Output: final answer, confidence summary, citations, loop metadata, trajectory id.

## Operational Notes

- Safety gate is post-coda by design.
- Feedback loop writes trajectory logs only; no automatic policy/prompt mutation.
- Prompt optimization remains offline + gated + human reviewed.
- Adapter selection is fully env-driven (`.env.example`), so deploys can change providers/stores without touching code.
- For external embeddings, keep `MYTHOS_PGVECTOR_DIMENSIONS` aligned with your embedding model output size.
- Retry/backoff currently targets transient network/5xx/429 and transient Postgres errors.

## Development Tasks

- `just test` — run tests
- `just lint` — compile sanity check

## Status

This repo provides a production-shaped scaffold with deterministic local behavior, suitable for replacing local provider/storage implementations with external services (pgvector, policy DB, E2B/Modal, hosted models).

## Chat UI Highlights

- High-fidelity conversation interface at `/app`
- Local session persistence with multi-thread switching
- Inline run telemetry (loops, halt reason, confidence, trajectory id)
- Built-in API base URL + API key controls for secured deployments
- Markdown rendering for model responses
