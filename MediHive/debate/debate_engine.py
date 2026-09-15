"""
debate/debate_engine.py

Phase 5: Compares the 5 agents' answers. If they disagree beyond a
threshold, runs ONE revision round where each agent sees every other
agent's answer + reasoning and is asked to reconsider.

Disagreement measure (kept deliberately simple for the 40% milestone):
we don't do semantic embedding similarity yet (that's more natural once
embeddings exist in the RAG phase). Instead we use confidence-spread +
a lightweight keyword-overlap heuristic. This is intentionally simple
and swappable later.
"""

import os
from agents.base_agent import AgentResponse, MedicalAgent
from memory.shared_memory import save_response

DISAGREEMENT_THRESHOLD = float(os.getenv("DEBATE_DISAGREEMENT_THRESHOLD", "0.35"))


from fusion.consensus import _extract_decision_key

COMMON_STOPS = {"the", "and", "for", "with", "this", "that", "from", "are", "was", "were", "has", "had"}


def _tokenize(text: str) -> set:
    words = [w.lower().strip(".,;:!?()[]\"'") for w in text.split()]
    return set(w for w in words if len(w) >= 2 and w not in COMMON_STOPS)


def _pairwise_overlap(a: str, b: str) -> float:
    """Similarity between two answers.
    Returns 0.0 (no overlap / total disagreement) to 1.0 (identical).
    """
    key_a = _extract_decision_key(a)
    key_b = _extract_decision_key(b)
    discrete_keys = {"A", "B", "C", "D", "YES", "NO", "MAYBE"}
    if key_a.upper() in discrete_keys and key_b.upper() in discrete_keys:
        return 1.0 if key_a.upper() == key_b.upper() else 0.0

    ta, tb = _tokenize(a), _tokenize(b)
    if not ta and not tb:
        return 1.0 if a.strip().lower() == b.strip().lower() else 0.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def compute_disagreement_score(responses: list[AgentResponse]) -> float:
    """Average pairwise dissimilarity across all agent answers.
    0.0 = full agreement, 1.0 = total disagreement."""
    if len(responses) < 2:
        return 0.0

    pairs = []
    for i in range(len(responses)):
        for j in range(i + 1, len(responses)):
            overlap = _pairwise_overlap(responses[i].answer, responses[j].answer)
            pairs.append(1 - overlap)

    return sum(pairs) / len(pairs)


def _build_revision_prompt(question: str, responses: list[AgentResponse], agent_name: str = "") -> str:
    summary = "\n\n".join(
        f"• Specialist: {r.agent} (Confidence: {r.confidence:.2f})\n"
        f"  Initial Stance: {r.answer}\n"
        f"  Clinical Rationale: {r.reasoning}"
        for r in responses
    )

    if agent_name == "Evidence Reviewer":
        role_directive = (
            "--- EVIDENCE REVIEWER AUDIT & SYNTHESIS DIRECTIVE ---\n"
            "As the Critical Evidence Reviewer and Epidemiologist, do NOT simply agree with peers:\n"
            "1. Audit Claims: Identify any unsupported assertions, over-generalizations, or outdated practices in peer arguments.\n"
            "2. Guideline Applicability: Verify whether cited clinical guidelines (CHEST, ESC, ACC/AHA, ASH) apply to this specific patient (checking exclusion criteria like recent surgery or renal disease).\n"
            "3. Evidence Weighting: Distinguish Level 1A prospective randomized trials from retrospective registries or expert opinion.\n"
            "4. Explicit Reassessment: State one of [Changed my recommendation], [Modified my recommendation], or [Maintained my recommendation] with recalibrated confidence."
        )
    else:
        role_directive = (
            "--- MANDATORY CLINICAL CHALLENGE & TRADE-OFF DIRECTIVE ---\n"
            "1. Mandatory Challenge: Explicitly challenge at least one competing recommendation:\n"
            "   - State which recommendation you are challenging.\n"
            "   - Identify the specific clinical, hemodynamic, or pharmacological weakness in that option.\n"
            "   - Explain why an alternative is safer or more effective, citing guidelines or clinical trial evidence.\n"
            "   - State what additional patient information (e.g., renal clearance, bleeding status) could change the decision.\n"
            "2. Patient-Specific Trade-Off: Analyze risks: Expected Benefit vs. Major Risk vs. Patient-Specific Concern.\n"
            "3. Explicit Reassessment Stance: Explicitly declare one of:\n"
            "   - [Changed my recommendation: ...]\n"
            "   - [Modified my recommendation: ...]\n"
            "   - [Maintained my recommendation: ...]\n"
            "   If maintaining, provide a new counter-justification addressing the strongest counter-argument.\n"
            "4. Recalibrate confidence realistically based on remaining uncertainty (do not automatically increase confidence)."
        )

    return (
        f"Clinical Case / Question:\n{question}\n\n"
        f"--- ROUND 1 SPECIALIST OPINIONS ---\n{summary}\n\n"
        f"--- ROUND 2 MULTI-AGENT CLINICAL DEBATE ---\n"
        f"{role_directive}\n\n"
        "Provide your revised step-by-step reasoning and final answer adhering strictly to the JSON schema."
    )


def run_debate(
    session_id: str,
    question: str,
    agents: list[MedicalAgent],
    round1_responses: list[AgentResponse],
) -> tuple[list[AgentResponse], bool]:
    """Returns (final_responses, debate_triggered).

    If disagreement is below threshold, round 1 responses are returned as-is.
    Otherwise, each agent gets one revision pass, which is saved to memory
    as round 2 and returned.
    """
    score = compute_disagreement_score(round1_responses)
    debate_triggered = score >= DISAGREEMENT_THRESHOLD

    if not debate_triggered:
        return round1_responses, False

    revised_responses = []

    for agent in agents:
        revision_prompt = _build_revision_prompt(question, round1_responses, agent_name=agent.name)
        revised = agent.run(revision_prompt)
        save_response(session_id, round_num=2, response=revised)
        revised_responses.append(revised)

    return revised_responses, True
