"""
fusion/consensus.py

v2: ITERATIVE FUSION (upgrade from the 40% build's single-shot
confidence-weighted pick).

How it's different from before:
  OLD: pick whichever single agent had the highest confidence. Done.
  NEW: run several weighting ROUNDS. In each round, every agent's
       weight is influenced by (a) its own stated confidence, (b) how
       much its answer agrees with the emerging group consensus, and
       (c) - when RAG was used - how well its reasoning aligns with the
       retrieved document context, so grounded answers are trusted more
       than answers that ignored the retrieved evidence. Weights are
       renormalized each round, so agents that keep agreeing with the
       group (and, when available, with the source material) gradually
       gain more influence over the final answer - this is the
       "iterative" part.

This mirrors real ensemble-method ideas (soft voting with iterative
re-weighting) rather than just "take the most confident answer".
"""

from agents.base_agent import AgentResponse

ITERATIONS = 3
RAG_ALIGNMENT_BONUS = 0.15  # extra weight for agents whose reasoning overlaps the retrieved context


def _tokenize(text: str) -> set:
    return set(w.lower().strip(".,;:!?") for w in text.split() if len(w) > 3)


def _similarity(a: str, b: str) -> float:
    """Jaccard word-overlap similarity, 0.0 (no overlap) - 1.0 (identical).
    Same lightweight approach used in debate_engine.py, kept consistent
    across the codebase rather than introducing a new metric.
    """
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _rag_alignment_score(response: AgentResponse, context: str) -> float:
    """How much does this agent's answer+reasoning overlap with the
    retrieved RAG context? Returns 0.0 if no context was retrieved
    (RAG inactive for this question), so behavior is unchanged when RAG
    isn't in play.
    """
    if not context:
        return 0.0
    combined = f"{response.answer} {response.reasoning}"
    return _similarity(combined, context)


def iterative_fusion(responses: list[AgentResponse], context: str = "") -> dict:
    """Runs ITERATIONS rounds of weighted re-scoring across all agent
    responses and returns the final weighted consensus.

    Round 0: initial weight = agent's own stated confidence, plus a RAG
             alignment bonus if the agent's reasoning overlaps retrieved
             context (rewards grounded answers over ungrounded guesses).

    Rounds 1..N: for each agent, weight is nudged toward the group's
             current weighted-average "reference answer" - agents whose
             answers keep agreeing with where the group is converging
             gain relative weight; outliers lose relative weight. This
             is a simple soft form of iterative consensus-building
             rather than a one-shot vote.
    """
    if not responses:
        return {"weights": {}, "reference_agent": None}

    # Round 0: initialize weights from confidence + RAG alignment
    weights = {}
    for r in responses:
        rag_bonus = RAG_ALIGNMENT_BONUS * _rag_alignment_score(r, context)
        weights[r.agent] = r.confidence + rag_bonus

    # Normalize
    total = sum(weights.values()) or 1.0
    weights = {k: v / total for k, v in weights.items()}

    # Iterative re-weighting rounds
    for _ in range(ITERATIONS):
        # Current "reference" agent = highest weighted right now
        reference = max(responses, key=lambda r: weights[r.agent])
        reference_text = f"{reference.answer} {reference.reasoning}"

        new_weights = {}
        for r in responses:
            agreement = _similarity(f"{r.answer} {r.reasoning}", reference_text)
            # Blend: keep 60% of current weight, nudge 40% toward agreement with reference
            new_weights[r.agent] = 0.6 * weights[r.agent] + 0.4 * agreement

        total = sum(new_weights.values()) or 1.0
        weights = {k: v / total for k, v in new_weights.items()}

    # Final pick: highest-weighted agent after all iterations
    final_agent = max(responses, key=lambda r: weights[r.agent])

    return {"weights": weights, "reference_agent": final_agent.agent}


def _extract_decision_key(text: str) -> str:
    """Normalize answer to a decision cluster key (A/B/C/D, yes/no/maybe, or cleaned snippet)."""
    import re
    if not text:
        return "unknown"
    text_clean = text.strip().lower()

    # Check yes/no/maybe
    for yn in ["yes", "no", "maybe"]:
        if re.search(rf"\b{yn}\b", text_clean):
            return yn

    # Check option letter A, B, C, D
    match = re.search(r'\b([a-d])\b', text_clean)
    if match:
        return match.group(1).upper()

    return text_clean[:30]


def build_consensus(responses: list[AgentResponse], debate_triggered: bool, context: str = "") -> dict:
    """Combine final-round agent responses into one consensus answer
    using Self-Consistency (SC) clustering + Iterative Soft-Voting Fusion.
    """
    if not responses:
        return {
            "consensus_answer": "No response produced.",
            "consensus_reasoning": "",
            "lead_agent": "None",
            "average_confidence": 0.0,
            "fusion_weighted_confidence": 0.0,
            "fusion_weights": {},
            "debate_triggered": debate_triggered,
            "agent_breakdown": [],
        }

    fusion_result = iterative_fusion(responses, context=context)
    weights = fusion_result["weights"]

    # Group responses by Self-Consistency (SC) decision cluster
    clusters = {}
    for r in responses:
        key = _extract_decision_key(r.answer)
        if key not in clusters:
            clusters[key] = {"total_weight": 0.0, "responses": []}
        clusters[key]["total_weight"] += weights.get(r.agent, 0.0)
        clusters[key]["responses"].append(r)

    # Sort clusters by cumulative weight
    sorted_clusters = sorted(clusters.keys(), key=lambda k: clusters[k]["total_weight"], reverse=True)
    winning_key = sorted_clusters[0]
    winning_responses = clusters[winning_key]["responses"]

    # Lead agent = highest-weighted agent within the winning cluster
    lead_response = max(winning_responses, key=lambda r: weights.get(r.agent, 0.0))

    # Detect secondary reasonable alternative if notable clinical support exists
    alternative_option = None
    alternative_weight = 0.0
    if len(sorted_clusters) > 1:
        sec_key = sorted_clusters[1]
        sec_weight = clusters[sec_key]["total_weight"]
        if sec_weight >= 0.12:
            sec_lead = max(clusters[sec_key]["responses"], key=lambda r: weights.get(r.agent, 0.0))
            alternative_option = f"{sec_lead.agent}: {sec_lead.answer}"
            alternative_weight = round(sec_weight, 3)

    avg_confidence = sum(r.confidence for r in responses) / len(responses)
    weighted_confidence = sum(r.confidence * weights[r.agent] for r in responses)

    return {
        "consensus_answer": lead_response.answer,
        "consensus_reasoning": lead_response.reasoning,
        "lead_agent": lead_response.agent,
        "preferred_option": lead_response.answer,
        "reasonable_alternative": alternative_option,
        "alternative_weight": alternative_weight,
        "consensus_cluster": winning_key,
        "cluster_support_weight": round(clusters[winning_key]["total_weight"], 3),
        "average_confidence": round(avg_confidence, 3),
        "fusion_weighted_confidence": round(weighted_confidence, 3),
        "fusion_weights": {agent: round(w, 3) for agent, w in weights.items()},
        "debate_triggered": debate_triggered,
        "agent_breakdown": [
            {
                "agent": r.agent,
                "answer": r.answer,
                "reasoning": r.reasoning,
                "confidence": r.confidence,
                "fusion_weight": round(weights[r.agent], 3),
            }
            for r in responses
        ],
    }

