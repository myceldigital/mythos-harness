# Mythos Quality + Eval Upgrade Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Turn Mythos from a scaffold-like orchestration runtime into a materially better reasoning wrapper, then benchmark it against four strong base models on the Aurora Ruling prompt.

**Architecture:** Replace placeholder reasoning passes with stateful model-driven phases: structured extraction in prelude, hypothesis refinement in solve, contradiction-focused verification, evidence-driven repair, and format-aware coda generation. Then add a repeatable eval script that runs base-model direct completions and Mythos(GPT-5.4-all-roles), scores outputs against the user rubric, and saves results.

**Tech Stack:** Python 3.11, FastAPI/LangGraph runtime, OpenRouter-compatible chat completions, pytest, local wrapper scripts.

---

### Task 1: Capture current weak spots

**Objective:** Record where Mythos is currently hard-coded/scaffold-like.

**Files:**
- Inspect: `src/mythos_harness/core/prelude.py`
- Inspect: `src/mythos_harness/core/loop.py`
- Inspect: `src/mythos_harness/core/coda.py`

**Step 1: Note placeholder behavior**
- Prelude seeds a generic hypothesis instead of reasoning over the prompt.
- Solve appends a canned sentence.
- Verify only judges internal consistency of the canned answer.
- Coda style-harmonizes scaffold text instead of composing a grounded final answer.

**Step 2: Verify this is the quality bottleneck**
- Re-run `mythos-ask --meta` on a test prompt.
- Confirm output is scaffold-like and not query-specific.

---

### Task 2: Add robust JSON extraction helpers

**Objective:** Support model responses wrapped in markdown fences or surrounding prose.

**Files:**
- Modify: `src/mythos_harness/core/triage.py`
- Test: `tests/test_triage.py`

**Step 1: Extend parsing helper**
- Add helper that extracts the first balanced JSON object from raw text.
- Keep fallback behavior if parsing still fails.

**Step 2: Add tests**
- Test plain JSON parsing.
- Test fenced JSON parsing.
- Test fallback on invalid payload.

---

### Task 3: Make prelude query-aware

**Objective:** Seed Mythos with extracted facts, assumptions, contradictions, and candidate answer instead of a canned hypothesis.

**Files:**
- Modify: `src/mythos_harness/core/prelude.py`
- Modify if needed: `src/mythos_harness/core/state.py`
- Test: `tests/test_reasoning_phases.py`

**Step 1: Ask base model for structured prelude JSON**
- Include query, retrieved memories, and constraints.
- Request grounded facts, assumptions, contradictions, candidate answer, reasoning bullets, and initial confidence.

**Step 2: Parse into structured state**
- Populate `facts`, `assumptions`, contradictions, and initial hypothesis.
- Preserve local deterministic fallback when JSON parse fails.

**Step 3: Test**
- Use a fake provider returning deterministic JSON.
- Assert Mythos state becomes query-specific.

---

### Task 4: Replace solve/verify/repair placeholders with evidence-driven phases

**Objective:** Each phase should materially improve or challenge the hypothesis.

**Files:**
- Modify: `src/mythos_harness/core/loop.py`
- Test: `tests/test_reasoning_phases.py`

**Step 1: Solve phase**
- Ask model to update the top hypothesis with best current answer, explicit evidence references, and confidence.

**Step 2: Verify phase**
- Ask judge model to find rule-order mistakes, overlooked contradictions, arithmetic/time conversion mistakes, and inconsistencies.
- Parse structured result with `passes`, `issues`, `missing_checks`, `confidence_adjustment`.

**Step 3: Repair phase**
- If verify found issues, ask model to produce a corrected answer and revised reasoning.

**Step 4: Test**
- Fake provider should show issue detection and corrected answer propagation.

---

### Task 5: Make coda produce the user-requested final format

**Objective:** Final answer should be query-aware and follow requested output constraints exactly.

**Files:**
- Modify: `src/mythos_harness/core/coda.py`
- Test: `tests/test_reasoning_phases.py`

**Step 1: Build synthesis prompt from final hypothesis + structured state**
- Include facts, assumptions, contradictions, and verification artifacts.
- Tell style/final model to obey the user’s requested output format exactly.

**Step 2: Finalize metadata**
- Keep confidence summary/citations.
- Ensure final answer is not scaffold boilerplate.

**Step 3: Test**
- Assert final output contains requested fields when the prompt asks for them.

---

### Task 6: Preserve configurable branch model fix

**Objective:** Keep the earlier OpenRouter compatibility fix intact.

**Files:**
- Inspect/modify if needed: `src/mythos_harness/config.py`
- Inspect/modify if needed: `src/mythos_harness/core/branch_manager.py`
- Inspect/modify if needed: `src/mythos_harness/core/service.py`
- Test: `tests/test_branch_model_config.py`

**Step 1: Ensure no regressions**
- Confirm `model_branch_alt` remains configurable.

**Step 2: Re-run regression test**
- `python -m pytest tests/test_branch_model_config.py -q`

---

### Task 7: Add repeatable eval harness

**Objective:** Run the Aurora Ruling prompt against four direct models and Mythos(GPT-5.4 all roles), then score results.

**Files:**
- Create: `scripts/eval_aurora.py`
- Create: `evals/aurora_prompt.txt`
- Create: `evals/aurora_results.json`

**Step 1: Store the prompt and rubric**
- Include expected-correct answer path and scoring rubric.

**Step 2: Implement eval runner**
- Call OpenRouter directly for 4 chosen base models.
- Call local Mythos wrapper with all model roles forced to `openai/gpt-5.4`.
- Parse outputs and score correctness/trap detection/calibration/faithfulness.

**Step 3: Save raw outputs + scores**
- Emit machine-readable JSON results.

---

### Task 8: Verify and summarize

**Objective:** Ensure code quality and produce a concise decision summary.

**Files:**
- Test: `tests/test_branch_model_config.py`
- Test: `tests/test_triage.py`
- Test: `tests/test_api.py`
- Test: `tests/test_reasoning_phases.py`
- Review: git diff

**Step 1: Run focused pytest suite**
```bash
cd /home/matthew/mythos-harness
/home/matthew/.local/bin/uv run --project /home/matthew/mythos-harness python -m pytest \
  tests/test_branch_model_config.py tests/test_triage.py tests/test_api.py tests/test_reasoning_phases.py -q
```

**Step 2: Run eval harness**
```bash
cd /home/matthew/mythos-harness
/home/matthew/.local/bin/uv run --project /home/matthew/mythos-harness python scripts/eval_aurora.py
```

**Step 3: Review diff and results**
- Summarize what improved.
- Note whether Mythos beats or merely matches direct GPT-5.4.
