from mythos_harness.budget import EscalationPolicy, InferenceBudget
from mythos_harness.decision import (
    ApprovalRecord,
    AuditBundle,
    DecisionMemo,
    EvidenceAdmissibility,
    EvidencePack,
    EvidenceReliability,
    EvidenceSource,
    ReviewDecision,
    create_decision_run,
)
from mythos_harness.panels import default_roles_for_domain


def test_decision_run_evidence_memo_and_audit_bundle_smoke() -> None:
    run = create_decision_run(
        "Should we proceed with the strategic initiative?",
        domain="pharma",
        risk_level="high",
        execution_mode="deep",
    )

    evidence_pack = EvidencePack(name="Synthetic pharma evidence pack")
    source = EvidenceSource(
        title="Synthetic diligence note",
        reliability=EvidenceReliability.MEDIUM,
        admissibility=EvidenceAdmissibility.ADMISSIBLE,
    )
    claim = source.add_claim("The initiative has material clinical and regulatory uncertainty.")
    evidence_pack.add_source(source)
    run.attach_evidence_pack(evidence_pack)

    branch = run.add_branch("bear_case", "Proceeding may expose the company to asymmetric downside.")
    branch.evidence_claim_ids.append(claim.claim_id)
    run.add_assumption("Clinical endpoint assumptions remain valid.", importance="high")
    run.add_contradiction("Commercial optimism conflicts with limited clinical evidence.", severity="high")
    run.complete(recommendation="Proceed only after additional diligence.", confidence=0.62)

    memo = DecisionMemo(
        run_id=run.run_id,
        title="Synthetic Pharma Second Opinion",
        recommendation=run.recommendation or "No recommendation",
        confidence=run.confidence,
    )
    memo.add_section("Strongest Case Against", branch.thesis, evidence_claim_ids=[claim.claim_id])

    approval = ApprovalRecord(
        run_id=run.run_id,
        reviewer="expert-reviewer@example.com",
        decision=ReviewDecision.CHALLENGE,
        note="Request more evidence before approval.",
    )
    audit_bundle = AuditBundle(
        run_id=run.run_id,
        evidence_pack_id=evidence_pack.pack_id,
        memo_id=memo.memo_id,
        approval_ids=[approval.approval_id],
    )

    assert run.status == "completed"
    assert evidence_pack.claims == [claim]
    assert "Strongest Case Against" in memo.to_markdown()
    assert audit_bundle.run_id == run.run_id


def test_budget_and_panel_roles_smoke() -> None:
    budget = InferenceBudget(max_tokens=100, max_cost_usd=1.0, escalation_policy=EscalationPolicy.ON_HIGH_STAKES)
    assert budget.can_spend(estimated_tokens=50, estimated_cost_usd=0.25).allowed
    budget.record_spend(tokens=80, cost_usd=0.75)
    assert not budget.can_spend(estimated_tokens=30, estimated_cost_usd=0.1).allowed

    roles = default_roles_for_domain("pharma")
    role_names = {role.name for role in roles}
    assert "clinical_skeptic" in role_names
    assert "regulatory_skeptic" in role_names
    assert "bear_case" in role_names
