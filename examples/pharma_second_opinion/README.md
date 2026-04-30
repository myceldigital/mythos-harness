# Pharma Second-Opinion Demo

This example is the canonical Mythos high-stakes demo.

It does not claim to make clinical, regulatory, investment, or legal decisions. It demonstrates the shape of a premium model-harness workflow: slow, adversarial, evidence-aware, and reviewable.

## Scenario

A pharmaceutical executive is evaluating whether to proceed with a high-cost strategic initiative such as an acquisition, pivotal trial strategy, or regulatory pathway.

The goal is not to get a fast answer.

The goal is to produce a second-opinion memo that an expert committee can challenge.

## Prompt

```text
Act as Mythos, a high-stakes second-opinion reasoning harness.

We are evaluating whether to proceed with a multi-billion-dollar pharmaceutical strategic initiative.

Produce a decision memo with:

1. Executive recommendation.
2. Strongest case for proceeding.
3. Strongest case against proceeding.
4. Clinical risk assumptions.
5. Regulatory risk assumptions.
6. Commercial risk assumptions.
7. Financial downside exposure.
8. Missing evidence.
9. What would change the conclusion.
10. Confidence level and why it is not higher.

Do not present the output as final truth. Present it as a structured second opinion for expert review.
```

## Local API Call

```bash
curl -X POST http://localhost:8080/v1/mythos/complete \
  -H "content-type: application/json" \
  -d '{
    "query": "Act as Mythos, a high-stakes second-opinion reasoning harness. We are evaluating whether to proceed with a multi-billion-dollar pharmaceutical strategic initiative. Produce a decision memo with executive recommendation, strongest case for proceeding, strongest case against proceeding, clinical risk assumptions, regulatory risk assumptions, commercial risk assumptions, financial downside exposure, missing evidence, what would change the conclusion, and confidence level. Present it as a structured second opinion for expert review, not final truth.",
    "thread_id": "pharma-second-opinion-demo",
    "constraints": {
      "execution_mode": "deep",
      "domain": "pharma",
      "risk_level": "high"
    }
  }'
```

## What This Demo Should Eventually Show

- Evidence room setup.
- Expert-role branch spawning.
- Assumption ledger.
- Contradiction register.
- Independent judge pass.
- Decision memo rendering.
- Human review status.
- Audit bundle export.
- Direct-model baseline vs Mythos-run comparison.
