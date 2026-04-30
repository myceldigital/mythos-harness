# Evaluation Strategy

The central Mythos claim is not that it uses more tokens.

The claim is that a serious harness can improve decision quality enough to justify extra cost, latency, and model calls.

Therefore Mythos needs benchmark reports that compare direct model calls against Mythos-wrapped runs.

## Core Comparison

```text
A. Base model direct answer
B. Base model with a strong single prompt
C. Base model with simple self-critique
D. Mythos full harness
E. Mythos full harness with independent judge model
```

## Target Metrics

| Metric | Question |
|---|---|
| Factuality | Did the output make fewer unsupported claims? |
| Reasoning quality | Did it handle ambiguity and tradeoffs better? |
| Calibration | Did confidence match evidence strength? |
| Assumption discovery | Did it expose hidden premises? |
| Counterargument quality | Did it produce serious opposing views? |
| Missing-evidence detection | Did it say what evidence is needed before deciding? |
| Decision usefulness | Would an expert committee prefer it? |
| Cost efficiency | Was the improvement worth the extra token/cost/latency budget? |

## Task Families

Initial benchmark tasks should include:

1. Ambiguous executive decisions.
2. Pharmaceutical second-opinion memos.
3. Investment committee reviews.
4. Security incident containment decisions.
5. Contradictory document synthesis.
6. Forecasting under uncertainty.
7. Strategy pre-mortems.
8. Legal or policy-style risk reviews.

## Output Artifacts

Each benchmark should save:

- task input,
- baseline answer,
- Mythos answer,
- token/cost/latency metadata,
- judge scores,
- expert preference if available,
- trajectory ID,
- and final evaluation report.

## Honest Claim Standard

Before publishing uplift claims, Mythos should be able to show:

```text
same base model + same task set + direct call baseline vs Mythos harness
```

The README can state the ambition now:

> Mythos is designed to increase decision quality per token.

It should not claim universal or staggering improvement until evals prove it.
