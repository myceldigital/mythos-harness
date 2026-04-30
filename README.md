# Mythos Harness

<p align="center">
  <strong>The premium reasoning harness for high-stakes AI decisions.</strong>
</p>

<p align="center">
  <em>When being wrong costs more than thinking, Mythos turns expensive inference into deliberate, auditable judgment.</em>
</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/github/license/myceldigital/mythos-harness">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-runtime-green">
  <img alt="LangGraph" src="https://img.shields.io/badge/LangGraph-orchestration-purple">
  <img alt="Status" src="https://img.shields.io/badge/status-v0.3%20scaffold-orange">
</p>

---

## The Short Version

Most AI systems optimize for cheap, instant answers.

**Mythos is built for the opposite case:** decisions where the cost of being wrong is far greater than the cost of additional compute.

As AI usage scales and raw model compute becomes more constrained, value will shift from simple model access to the harnesses that extract more intelligence, confidence, and decision quality from every expensive token.

Mythos wraps base models in a deliberate reasoning process:

- triage the decision,
- decompose the problem,
- retrieve relevant memory,
- generate competing hypotheses,
- challenge the leading answer,
- repair contradictions,
- calibrate confidence,
- apply policy gates,
- log the reasoning trajectory,
- and produce an auditable final answer.

It is not the fastest way to call an LLM.

It is the system you use when a wrong answer could cost millions or billions.

---

## The Mythos Thesis

Frontier model quality is no longer limited only by model weights.

It is increasingly limited by **how intelligently expensive inference is allocated**.

A raw model call spends tokens once. A model harness spends tokens strategically:

1. First on triage.
2. Then on decomposition.
3. Then on competing hypotheses.
4. Then on adversarial verification.
5. Then on contradiction repair.
6. Then on synthesis.
7. Then on safety and policy review.
8. Then on trajectory logging for future evaluation.

The goal is not merely to use more tokens.

The goal is to increase **cognitive yield per token**.

Mythos is designed around a simple economic premise:

> When the downside of a bad answer is asymmetric, slow, expensive, structured inference becomes rational.

---

## Why Mythos Exists

Imagine a senior executive at a fortune 50 company preparing to make a strategic decision with a potential multi-billion-dollar cost.

They do not need a chatbot.

They need a system that can:

- state the strongest case for the decision,
- state the strongest case against it,
- expose hidden assumptions,
- identify what evidence is missing,
- challenge internal consensus,
- surface regulatory, clinical, commercial, financial, and reputational risks,
- explain what would change the recommendation,
- and produce a decision memo an expert can review.

That is the class of problem Mythos is built for.

Mythos is not a replacement for expert judgment.

It is a harness for producing better expert judgment support from base models.

---

## What Mythos Is

Mythos Harness is a **FastAPI + LangGraph orchestration runtime** for building deliberate AI reasoning systems.

It implements an architecture of:

- **Front-door triage** before deep reasoning.
- **Structured latent state** instead of opaque hidden strings.
- **Branch manager** for competing hypotheses.
- **Phase-keyed reasoning loop**: `explore → solve → verify → repair → synthesize`.
- **Five-model abstraction bus**: `base`, `fast`, `judge`, `code/math`, `style`.
- **Session memory and pgvector retrieval**.
- **Post-coda safety gate**.
- **Passive feedback loop with governance-safe boundaries**.
- **Server-Sent Events streaming** for live progressive output.
- **Web console** at `/app`.
- **Trajectory logging** for audit, evaluation, and offline improvement.

---

## What Mythos Is Not

Mythos is not:

- a generic chatbot wrapper,
- a toy agent demo,
- a promise that every answer is correct,
- a regulated medical, legal, financial, or clinical decision engine out of the box,
- an autonomous replacement for expert review,
- or a shortcut around human accountability.

The current repo is a **production-shaped scaffold**.

It provides the architecture, runtime, API, memory hooks, model routing, safety gate, observability, and local deterministic behaviour needed to build toward high-stakes model-harness workflows.

The serious-decision layer still needs deeper evidence ingestion, stronger domain-specific expert branches, benchmark reports, human review workflows, and audit-grade provenance.

---

## Core Idea

```text
Raw model call:
  prompt → model → answer

Mythos run:
  request
    → triage
    → memory retrieval
    → structured state
    → branch competing hypotheses
    → deliberate phase loop
    → judge pass
    → repair contradictions
    → synthesize
    → safety gate
    → trajectory log
    → auditable answer
```

---

## Architecture

```mermaid
flowchart TB
    %% =========================
    %% Economic Thesis
    %% =========================
    subgraph Thesis["Mythos Thesis"]
        Scarcity["Compute becomes constrained<br/>as AI usage scales"]
        ExpensiveTokens["Tokens become strategic<br/>not disposable"]
        HarnessAlpha["Value shifts to harnesses<br/>that increase decision quality per token"]
    end

    Scarcity --> ExpensiveTokens --> HarnessAlpha

    %% =========================
    %% High Stakes Context
    %% =========================
    subgraph HighStakes["High-Stakes Decision Context"]
        Exec["Executive / Expert / Committee"]
        Decision["Decision with asymmetric downside<br/>clinical, financial, legal, strategic, safety"]
        CostWrong["Cost of being wrong:<br/>millions to billions"]
    end

    Exec --> Decision --> CostWrong
    CostWrong --> Interface

    %% =========================
    %% Interface Layer
    %% =========================
    subgraph Interface["Mythos Interface"]
        WebApp["/app<br/>Decision Console"]
        CompleteAPI["POST /v1/mythos/complete<br/>blocking completion"]
        StreamAPI["POST /v1/mythos/stream<br/>SSE streaming"]
        Constraints["Constraints<br/>depth, risk, budget, policy, domain"]
    end

    WebApp --> CompleteAPI
    WebApp --> StreamAPI
    Constraints --> CompleteAPI
    Constraints --> StreamAPI

    %% =========================
    %% Serving Layer
    %% =========================
    subgraph Serving["FastAPI Serving Layer"]
        Middleware["Middleware<br/>API keys, rate limits, request IDs, metrics"]
        Router["Routes + Schemas"]
        Health["/healthz /readyz /metrics"]
    end

    CompleteAPI --> Middleware
    StreamAPI --> Middleware
    Middleware --> Router
    Middleware --> Health

    %% =========================
    %% Harness Core
    %% =========================
    subgraph Harness["Mythos Model Harness"]
        Triage["1. Front-Door Triage<br/>task type, difficulty, ambiguity, risk, mode"]
        Memory["2. Session + Memory Retrieval<br/>thread snapshot, vector similarity"]
        Prelude["3. Prelude Builder<br/>goals, constraints, encoded input"]
        State["4. Structured Latent State<br/>facts, assumptions, hypotheses, contradictions, tests, confidence"]
        Branches["5. Branch Manager<br/>spawn, prune, collapse competing hypotheses"]
        Loop{"6. Phase-Keyed Loop"}
        Explore["explore"]
        Solve["solve"]
        Verify["verify"]
        Repair["repair"]
        Synthesize["synthesize"]
        Coda["7. Coda Builder<br/>best state → final answer"]
        Safety["8. Post-Coda Safety Gate<br/>policy lookup, revision path"]
        Feedback["9. Feedback Logger<br/>trajectory, metadata, offline eval trail"]
    end

    Router --> Triage
    Triage --> Memory
    Memory --> Prelude
    Prelude --> State
    State --> Branches
    Branches --> Loop

    Loop --> Explore
    Explore --> Solve
    Solve --> Verify
    Verify -->|contradiction or weak confidence| Repair
    Repair --> Loop
    Verify -->|confidence sufficient| Synthesize
    Synthesize --> Coda
    Coda --> Safety
    Safety --> Feedback

    %% =========================
    %% Model Bus
    %% =========================
    subgraph ModelBus["Five-Model Abstraction Bus"]
        Fast["Fast Model<br/>triage, routing, cheap passes"]
        Base["Base Model<br/>main reasoning"]
        Judge["Judge Model<br/>verification, critique, consistency"]
        CodeMath["Code/Math Model<br/>specialist reasoning"]
        Style["Style Model<br/>final memo polish"]
    end

    Triage -.-> Fast
    Solve -.-> Base
    Verify -.-> Judge
    Repair -.-> Base
    Solve -.-> CodeMath
    Synthesize -.-> Style

    %% =========================
    %% Stores
    %% =========================
    subgraph Stores["Externalized Stores"]
        SessionStore["Session Store<br/>memory or Postgres"]
        VectorStore["pgvector Memory<br/>similarity retrieval"]
        PolicyStore["Policy Store<br/>file or HTTP"]
        TrajectoryStore["Trajectory Store<br/>JSONL, Postgres, or HTTP"]
        Redis["Redis<br/>rate limits"]
        Prometheus["Prometheus<br/>metrics"]
    end

    Memory -.-> SessionStore
    Memory -.-> VectorStore
    Safety -.-> PolicyStore
    Feedback -.-> TrajectoryStore
    Middleware -.-> Redis
    Middleware -.-> Prometheus

    %% =========================
    %% Output
    %% =========================
    subgraph Output["High-Value Output"]
        Answer["Final Answer"]
        Confidence["Confidence Summary"]
        Citations["Citations / Grounded Facts"]
        LoopMeta["Loop Metadata"]
        TrajectoryID["Trajectory ID"]
        AuditTrail["Offline Audit Trail"]
    end

    Feedback --> Answer
    Feedback --> Confidence
    Feedback --> Citations
    Feedback --> LoopMeta
    Feedback --> TrajectoryID
    Feedback --> AuditTrail

    Answer --> Exec
```

---

## Where Mythos Fits

Use Mythos when:

- the task is ambiguous,
- the stakes are high,
- the answer needs to survive challenge,
- multiple interpretations are plausible,
- the cost of a false positive or false negative is large,
- the final output needs a reasoning trail,
- or a base model needs a stronger harness than a single prompt.

Do not use Mythos when:

- you need the cheapest possible answer,
- latency matters more than judgment quality,
- the task is simple and deterministic,
- or a direct model call is sufficient.

---

## Example Use Cases

### Pharmaceutical Second Opinion

A pharmaceutical executive wants a second opinion before committing capital to a clinical, regulatory, or acquisition strategy.

Mythos can be used to produce a structured review:

- strongest case for proceeding,
- strongest case against proceeding,
- hidden assumptions,
- missing evidence,
- clinical risk,
- regulatory risk,
- commercial risk,
- confidence level,
- and what would change the recommendation.

### Investment Committee Review

An investment committee wants an adversarial pre-mortem before approving a major allocation.

Mythos can help generate:

- base case,
- upside case,
- downside case,
- key uncertainties,
- disconfirming evidence,
- risk concentration,
- decision memo,
- and follow-up diligence questions.

### Security Incident Analysis

A security team wants to know whether an incident is actually contained.

Mythos can help reason through:

- competing breach hypotheses,
- containment assumptions,
- missing logs,
- likely attacker paths,
- confidence in remediation,
- and next verification steps.

### Founder or Executive Strategy

A founder wants a brutal second opinion before betting the company on a new product direction.

Mythos can help produce:

- strategic case,
- anti-case,
- competitor lens,
- customer adoption risk,
- resource risk,
- execution bottlenecks,
- and decision checkpoints.

---

## Quickstart

### 1. Create a Python environment

```bash
python --version
# Python 3.10+ recommended
```

### 2. Install dependencies

```bash
just install
```

### 3. Run the service

```bash
just run
```

### 4. Open the web console

```bash
open http://localhost:8080/app
```

### 5. Call the API directly

```bash
curl -X POST http://localhost:8080/v1/mythos/complete \
  -H "content-type: application/json" \
  -d '{
    "query": "Give me a migration plan from v0.2 to v0.3",
    "thread_id": "demo-1"
  }'
```

---

## Try a High-Stakes-Style Prompt

```bash
curl -X POST http://localhost:8080/v1/mythos/complete \
  -H "content-type: application/json" \
  -d '{
    "query": "Act as a second-opinion reasoning system. We are evaluating whether to proceed with a high-cost strategic initiative. Build the strongest case for proceeding, the strongest case against proceeding, identify hidden assumptions, list missing evidence, and produce a cautious recommendation with confidence and caveats.",
    "thread_id": "high-stakes-demo"
  }'
```

Expected output includes:

- final answer,
- confidence summary,
- citations / grounded facts where available,
- loop count,
- halt reason,
- trajectory ID,
- triage metadata.

---

## API

### `POST /v1/mythos/complete`

Blocking completion endpoint.

Input:

```json
{
  "query": "Your task or decision question",
  "thread_id": "optional-thread-id",
  "constraints": {
    "execution_mode": "deep"
  }
}
```

Output includes:

```json
{
  "answer": "...",
  "confidence_summary": "...",
  "citations": [],
  "loop_count": 0,
  "halt_reason": "...",
  "trajectory_id": "...",
  "triage": {}
}
```

### `POST /v1/mythos/stream`

Streaming endpoint using Server-Sent Events.

Input:

```json
{
  "query": "Your task or decision question",
  "thread_id": "optional-thread-id"
}
```

Event types:

```text
status
token
replace
final
done
```

Use this endpoint when you want live progressive rendering in a UI.

---

## Web Console

Mythos includes a high-fidelity chat and run-inspection UI at:

```text
http://localhost:8080/app
```

The console includes:

- conversation interface,
- local session persistence,
- multi-thread switching,
- tabbed run insights,
- triage payload view,
- request payload view,
- activity feed,
- inline run telemetry,
- loop count,
- halt reason,
- confidence summary,
- trajectory ID,
- task type,
- citations,
- API base URL control,
- API key control,
- execution mode control,
- constraints controls,
- connection test for `/healthz` and `/readyz`,
- live SSE streaming,
- and markdown rendering for model responses.

---

## Model Provider Setup

Mythos can run with deterministic local behavior for development and can be configured to use hosted model providers.

### OpenRouter

Recommended for multi-model routing.

```bash
export MYTHOS_PROVIDER_BACKEND=openrouter
export MYTHOS_PROVIDER_API_KEY=<your_openrouter_key>

export MYTHOS_MODEL_BASE=anthropic/claude-3.5-sonnet
export MYTHOS_MODEL_FAST=anthropic/claude-3.5-haiku
export MYTHOS_MODEL_JUDGE=openai/gpt-4o-mini
```

### Any OpenAI-Compatible Provider

```bash
export MYTHOS_PROVIDER_BACKEND=openai_compatible
export MYTHOS_PROVIDER_API_KEY=<your_provider_key>
export MYTHOS_PROVIDER_BASE_URL=https://api.openai.com/v1
```

### Optional Separate Judge Backend

For stronger second-opinion architecture, you can route the judge model through a separate provider or model family.

```bash
export MYTHOS_JUDGE_PROVIDER_BACKEND=openrouter
export MYTHOS_JUDGE_PROVIDER_API_KEY=<judge_key>
```

This is useful when you want the verifier to be meaningfully independent from the main reasoning model.

---

## Five-Model Bus

Mythos is designed around a model abstraction bus rather than a single model call.

| Role | Purpose |
|---|---|
| `fast` | Triage, routing, cheap passes |
| `base` | Main reasoning |
| `judge` | Critique, verification, consistency checks |
| `code/math` | Specialist reasoning |
| `style` | Final synthesis and memo polish |

This lets you allocate expensive inference where it matters most.

Cheap model calls can classify and route. Stronger models can reason. Independent judge models can challenge. Specialist models can handle technical subtasks. Style models can polish the final answer.

---

## Externalized Stores

### Postgres + pgvector

Run the bootstrap SQL:

```bash
psql "$MYTHOS_POSTGRES_DSN" -f sql/bootstrap_postgres.sql
```

If you previously used `VECTOR(16)` in `mythos.session_snapshots`, run:

```bash
psql "$MYTHOS_POSTGRES_DSN" -f sql/migrations/20260422_vector_16_to_1536.sql
```

For idempotent migration management:

```bash
just migrate
```

Set store backends:

```bash
export MYTHOS_POSTGRES_DSN=postgresql://user:pass@localhost:5432/mythos
export MYTHOS_SESSION_STORE_BACKEND=postgres
export MYTHOS_TRAJECTORY_STORE_BACKEND=postgres
```

### Embeddings

Local deterministic embeddings:

```bash
export MYTHOS_EMBEDDING_BACKEND=local
export MYTHOS_PGVECTOR_DIMENSIONS=1536
```

OpenAI-compatible embedding backend:

```bash
export MYTHOS_EMBEDDING_BACKEND=openai_compatible
export MYTHOS_EMBEDDING_MODEL=text-embedding-3-small
export MYTHOS_EMBEDDING_API_KEY=<embedding_key>
export MYTHOS_EMBEDDING_BASE_URL=https://api.openai.com/v1
```

Keep `MYTHOS_PGVECTOR_DIMENSIONS` aligned with your embedding model output size.

### Vector Similarity Retrieval

At request start, the orchestrator can perform similarity lookup over session snapshots.

Retrieved memories are injected as grounded facts during prelude.

Control retrieval depth with:

```bash
export MYTHOS_MEMORY_RETRIEVAL_K=3
```

### Remote Policy Store

```bash
export MYTHOS_POLICY_STORE_BACKEND=http
export MYTHOS_POLICY_HTTP_URL=https://policy.example.com/v1/mythos/policy
export MYTHOS_POLICY_HTTP_API_KEY=<policy_api_key>
```

### Remote Trajectory Warehouse

```bash
export MYTHOS_TRAJECTORY_STORE_BACKEND=http
export MYTHOS_TRAJECTORY_HTTP_URL=https://warehouse.example.com/v1/trajectories
export MYTHOS_TRAJECTORY_HTTP_API_KEY=<warehouse_api_key>
```

---

## Security and Resilience

### API Key Auth

```bash
export MYTHOS_API_AUTH_ENABLED=true
export MYTHOS_API_AUTH_KEYS=key_one,key_two
```

Clients can use either:

```text
x-api-key: <key>
```

or:

```text
Authorization: Bearer <key>
```

For enterprise secret hygiene, store SHA256 hashes instead of plaintext keys:

```bash
export MYTHOS_API_AUTH_KEY_HASHES=<sha256hex>,<sha256hex>
```

### Rate Limiting

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

### Retry and Backoff

```bash
export MYTHOS_RETRY_MAX_ATTEMPTS=3
export MYTHOS_RETRY_BASE_DELAY_S=0.25
export MYTHOS_RETRY_MAX_DELAY_S=2.0
export MYTHOS_RETRY_JITTER_S=0.05
```

Retry/backoff targets transient network errors, `5xx`, `429`, and transient Postgres errors.

---

## Observability and Readiness

Mythos includes production-oriented health and observability endpoints.

```text
GET /healthz
GET /readyz
GET /metrics
```

Features:

- liveness checks,
- dependency readiness checks,
- Prometheus metrics,
- request correlation IDs,
- configurable request ID header,
- structured access logs.

Request correlation IDs are attached via:

```text
x-request-id
```

Configure with:

```bash
export MYTHOS_REQUEST_ID_HEADER=x-request-id
export MYTHOS_ACCESS_LOG_ENABLED=true
```

---

## Operational Principles

### Safety Gate Is Post-Coda by Design

Mythos applies the safety gate after synthesis so that policy can evaluate the actual proposed answer, not just the original prompt.

### Feedback Is Passive by Default

The feedback loop writes trajectory logs only.

It does not automatically mutate prompts, policies, or model behavior.

### Optimization Is Offline and Governed

Prompt optimization and policy updates should remain:

- offline,
- evaluated,
- gated,
- and human reviewed.

### Providers and Stores Are Environment-Driven

Adapter selection is controlled through environment variables.

Deployments can change providers, models, session stores, policy stores, and trajectory stores without changing application code.

---

## Repo Layout

```text
src/mythos_harness/
  api/              # FastAPI routes + request/response schemas
  core/             # State model, triage, loop phases, coda, safety, feedback
  embeddings/       # Embedding provider adapters for pgvector session memory
  graph/            # LangGraph assembly and execution
  providers/        # Model provider abstraction + local deterministic provider
  storage/          # Session snapshots, trajectory logs, policy store
  main.py           # App entrypoint

config/             # Configuration files
docs/               # Documentation
scripts/            # Utility scripts
sql/                # Postgres and pgvector bootstrap/migrations
tests/              # Unit + route smoke tests

PROJECT_TECHNICAL_OVERVIEW.md
mythosv3_architecture.md
CHANGELOG.md
learnings.md
workflow_state.md
pyproject.toml
justfile
.env.example
```

---

## Development

Run tests:

```bash
just test
```

Run lint / compile sanity check:

```bash
just lint
```

Run migrations:

```bash
just migrate
```

Run service:

```bash
just run
```

---

## Current Status

Mythos Harness v0.3 is a production-shaped scaffold with deterministic local behavior.

It is suitable for replacing local provider and storage implementations with external services such as:

- hosted model providers,
- OpenRouter,
- OpenAI-compatible APIs,
- Postgres,
- pgvector,
- remote policy DBs,
- remote trajectory warehouses,
- Redis,
- and Prometheus.

It is not yet a complete regulated decision platform.

The repo currently provides the harness spine:

- triage,
- structured latent state,
- phase loop,
- branch manager,
- model bus,
- memory retrieval,
- safety gate,
- streaming API,
- web console,
- observability,
- trajectory logging,
- and configurable external stores.

---

## Roadmap Toward High-Stakes Decision Support

The next layer of Mythos should make the premium model-harness thesis measurable and enterprise-grade.

### Evidence and Retrieval

- Evidence-room ingestion.
- Source-grounded retrieval.
- Document packs.
- Evidence quality scoring.
- Citation provenance.
- Contradiction detection across sources.

### Expert-Panel Branching

- Bull case branch.
- Bear case branch.
- Regulatory skeptic branch.
- Clinical skeptic branch.
- Commercial skeptic branch.
- Security skeptic branch.
- CFO skeptic branch.
- Legal/compliance skeptic branch.
- Independent judge model pass.

### Decision Memo Outputs

- Executive recommendation.
- Assumption ledger.
- Strongest counterarguments.
- What would change the conclusion.
- Confidence and uncertainty.
- Sensitivity analysis.
- Follow-up diligence list.
- Audit bundle export.

### Long-Running Runs

- Durable async jobs.
- Resumable runs.
- Cancellation.
- Intermediate artifacts.
- Run comparison.
- Final report export.

### Evaluation

- Baseline model call vs Mythos-wrapped model.
- Accuracy uplift benchmarks.
- Calibration benchmarks.
- Contradiction-repair benchmarks.
- Expert preference studies.
- Cost-per-quality metrics.
- Cognitive yield per token.

### Governance

- Human review workflow.
- Policy packs.
- Approval states.
- Workspace-level audit trails.
- Model/provider separation for judge passes.
- Enterprise deployment templates.

---

## Benchmark Thesis

A model harness should be judged by whether it improves the output of base models enough to justify its extra cost.

Future benchmark reports should compare:

```text
base model direct call
vs
base model + Mythos harness
```

Across dimensions such as:

- factual accuracy,
- reasoning quality,
- calibration,
- robustness to ambiguity,
- ability to surface assumptions,
- ability to identify missing evidence,
- quality of counterarguments,
- expert preference,
- and final decision usefulness.

The core metric Mythos should optimize for is:

```text
decision quality per token
```

or:

```text
cognitive yield per token
```

---

## Responsible Use

Mythos is intended for decision support, adversarial review, and reasoning assistance.

It should not be used as the sole authority for medical, legal, financial, clinical, safety, regulatory, or other high-stakes decisions.

For consequential use cases:

- keep humans accountable,
- require expert review,
- preserve source material,
- log trajectories,
- evaluate outputs,
- document assumptions,
- and treat model output as a second opinion, not final truth.

---

## Why This Could Matter

If model access becomes commoditized, the next value layer is not simply the biggest model.

It is the system that knows how to spend inference.

Mythos is an attempt to build that layer:

```text
scarce compute
  → expensive tokens
  → need for better allocation
  → model harnesses
  → higher decision quality per token
```

The long-term vision is simple:

> Any base model should perform better when wrapped in a serious reasoning harness.

---

## Suggested Repository Description

Use this in the GitHub repo description field:

```text
Premium reasoning harness for high-stakes AI decisions: triage, branching hypotheses, verification, repair, memory, safety, streaming API, and audit trails.
```

## Suggested Topics

Add these GitHub topics for discoverability:

```text
ai-agents
agent-framework
llm
llmops
langgraph
fastapi
reasoning
agentic-ai
ai-orchestration
model-routing
model-harness
decision-support
ai-safety
pgvector
openrouter
sse
prometheus
```

---

## Contributing

Contributions are welcome.

High-leverage areas:

- benchmark tasks,
- high-stakes decision memo templates,
- expert-panel branch strategies,
- evidence ingestion,
- retrieval quality,
- model routing,
- judge-model evaluation,
- streaming UI improvements,
- deployment examples,
- policy packs,
- and documentation.

Before contributing, run:

```bash
just test
just lint
```

---

## License

MIT License.

See [`LICENSE`](LICENSE).

---

## Final Positioning

Mythos is not trying to be the cheapest way to call a model.

It is trying to become the harness you trust when the answer matters.

> Stop asking models for answers. Make them earn conclusions.