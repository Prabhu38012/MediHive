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

DISAGREEMENT_THRESHOLD = float(os.getenv("DEBATE_DISAGREEMENT_THRESHOLD", "0.5"))


def _tokenize(text: str) -> set:
    return set(w.lower().strip(".,;:!?") for w in text.split() if len(w) > 3)


def _pairwise_overlap(a: str, b: str) -> float:
    """Jaccard similarity between two answers' significant words.
    Returns 0.0 (no overlap) to 1.0 (identical)."""
    ta, tb = _tokenize(a), _tokenize(b)
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


def _build_revision_prompt(question: str, responses: list[AgentResponse]) -> str:
    summary = "\n\n".join(
        f"- Specialist: {r.agent} (Confidence: {r.confidence:.2f})\n"
        f"  Diagnosis/Answer: {r.answer}\n"
        f"  Clinical Rationale: {r.reasoning}"
        for r in responses
    )
    return (
        f"Clinical Case / Question:\n{question}\n\n"
        f"--- ROUND 1 SPECIALIST OPINIONS ---\n{summary}\n\n"
        f"--- DEBATE & REVISION INSTRUCTION ---\n"
        "Critically evaluate your peers' diagnoses and pharmacologic/pathophysiologic arguments. "
        "Check for potential diagnostic errors, missed drug mechanisms, or misinterpreted clinical findings. "
        "You may either maintain your position or revise your diagnosis if another specialist presented stronger evidence. "
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
    revision_prompt = _build_revision_prompt(question, round1_responses)

    for agent in agents:
        revised = agent.run(revision_prompt)
        save_response(session_id, round_num=2, response=revised)
        revised_responses.append(revised)

    return revised_responses, True
