"""Default expert-role branch templates.

These roles turn generic hypothesis branching into adversarial panels tailored to
high-stakes domains.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExpertRole:
    """A named reasoning branch role."""

    name: str
    objective: str
    challenge_prompt: str


GENERAL_ROLES: tuple[ExpertRole, ...] = (
    ExpertRole(
        "bull_case",
        "Build the strongest responsible case for proceeding.",
        "What evidence supports action, and what assumptions must hold?",
    ),
    ExpertRole(
        "bear_case",
        "Build the strongest responsible case against proceeding.",
        "What could make this decision fail, and what evidence is being underweighted?",
    ),
    ExpertRole(
        "cfo_skeptic",
        "Pressure-test cost, capital allocation, and downside exposure.",
        "Where could financial assumptions be fragile or asymmetric?",
    ),
    ExpertRole(
        "legal_compliance_skeptic",
        "Pressure-test legal, regulatory, and compliance exposure.",
        "What obligations, constraints, or review gates could block the recommendation?",
    ),
)

PHARMA_ROLES: tuple[ExpertRole, ...] = GENERAL_ROLES + (
    ExpertRole(
        "clinical_skeptic",
        "Challenge clinical efficacy, safety, trial design, and endpoint assumptions.",
        "What clinical evidence is insufficient or overinterpreted?",
    ),
    ExpertRole(
        "regulatory_skeptic",
        "Challenge approval pathway, labeling, post-market, and agency-risk assumptions.",
        "What regulatory uncertainty could materially change the decision?",
    ),
    ExpertRole(
        "commercial_skeptic",
        "Challenge market size, adoption, pricing, reimbursement, and competitive assumptions.",
        "What commercial premise is most likely to be wrong?",
    ),
)

INVESTMENT_ROLES: tuple[ExpertRole, ...] = GENERAL_ROLES + (
    ExpertRole(
        "macro_skeptic",
        "Challenge macro, liquidity, rate, and regime assumptions.",
        "What market regime would invalidate the investment case?",
    ),
    ExpertRole(
        "portfolio_risk_skeptic",
        "Challenge correlation, concentration, sizing, and drawdown exposure.",
        "How does this decision behave in the left tail?",
    ),
)

SECURITY_ROLES: tuple[ExpertRole, ...] = GENERAL_ROLES + (
    ExpertRole(
        "attacker_modeler",
        "Reason from the adversary perspective and identify missed paths.",
        "How could the attacker still maintain access or exploit assumptions?",
    ),
    ExpertRole(
        "containment_skeptic",
        "Challenge incident containment and remediation confidence.",
        "What evidence proves containment rather than merely suggesting it?",
    ),
)


def default_roles_for_domain(domain: str) -> tuple[ExpertRole, ...]:
    """Return branch roles for a decision domain."""

    normalized = domain.strip().lower().replace("-", "_")
    if normalized in {"pharma", "pharmaceutical", "biotech", "clinical"}:
        return PHARMA_ROLES
    if normalized in {"investment", "finance", "capital_allocation"}:
        return INVESTMENT_ROLES
    if normalized in {"security", "incident", "cybersecurity"}:
        return SECURITY_ROLES
    return GENERAL_ROLES
