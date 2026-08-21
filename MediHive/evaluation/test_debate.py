"""
evaluation/test_debate.py

Basic tests for the disagreement scoring logic (Phase 5).
Run with: pytest evaluation/test_debate.py
"""

from datetime import datetime, timezone
from agents.base_agent import AgentResponse
from debate.debate_engine import compute_disagreement_score, _pairwise_overlap


def _mk_response(agent, answer, confidence=0.8):
    return AgentResponse(
        agent=agent,
        question="test question",
        answer=answer,
        reasoning="test reasoning",
        confidence=confidence,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def test_identical_answers_have_zero_disagreement():
    responses = [
        _mk_response("A", "Take ibuprofen for the headache"),
        _mk_response("B", "Take ibuprofen for the headache"),
    ]
    score = compute_disagreement_score(responses)
    assert score == 0.0


def test_completely_different_answers_have_high_disagreement():
    responses = [
        _mk_response("A", "Immediate surgery is required urgently"),
        _mk_response("B", "Rest and hydration should resolve symptoms"),
    ]
    score = compute_disagreement_score(responses)
    assert score > 0.8


def test_pairwise_overlap_symmetry():
    a = "chest pain suggests cardiac event"
    b = "cardiac event suggests chest pain"
    assert _pairwise_overlap(a, b) == _pairwise_overlap(b, a)


def test_single_response_has_no_disagreement():
    responses = [_mk_response("A", "Some answer")]
    assert compute_disagreement_score(responses) == 0.0
