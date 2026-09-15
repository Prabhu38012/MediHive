import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    assert score == 0.0, f"Expected 0.0, got {score}"


def test_completely_different_answers_have_high_disagreement():
    responses = [
        _mk_response("A", "Immediate surgery is required urgently"),
        _mk_response("B", "Rest and hydration should resolve symptoms"),
    ]
    score = compute_disagreement_score(responses)
    assert score > 0.8, f"Expected >0.8, got {score}"


def test_pairwise_overlap_symmetry():
    a = "chest pain suggests cardiac event"
    b = "cardiac event suggests chest pain"
    assert _pairwise_overlap(a, b) == _pairwise_overlap(b, a)


def test_single_response_has_no_disagreement():
    responses = [_mk_response("A", "Some answer")]
    assert compute_disagreement_score(responses) == 0.0


def test_mcq_identical_letter_answers_have_zero_disagreement():
    responses = [
        _mk_response("Agent 1", "A"),
        _mk_response("Agent 2", "A"),
        _mk_response("Agent 3", "Option A is the most likely diagnosis"),
    ]
    score = compute_disagreement_score(responses)
    assert score == 0.0, f"Expected 0.0 for identical MCQ choices, got {score}"


def test_mcq_differing_letter_answers_have_high_disagreement():
    responses = [
        _mk_response("Agent 1", "A"),
        _mk_response("Agent 2", "B"),
    ]
    score = compute_disagreement_score(responses)
    assert score == 1.0, f"Expected 1.0 for conflicting MCQ choices, got {score}"


def test_pubmedqa_identical_binary_decisions_have_zero_disagreement():
    responses = [
        _mk_response("Agent 1", "yes"),
        _mk_response("Agent 2", "yes"),
        _mk_response("Agent 3", "The evidence supports yes"),
    ]
    score = compute_disagreement_score(responses)
    assert score == 0.0, f"Expected 0.0 for unanimous yes decisions, got {score}"


def test_five_agent_unanimous_panel_does_not_trigger_disagreement():
    responses = [
        _mk_response("General Physician", "C"),
        _mk_response("Cardiologist", "C"),
        _mk_response("Neurologist", "C"),
        _mk_response("Pharmacologist", "C"),
        _mk_response("Evidence Reviewer", "C"),
    ]
    score = compute_disagreement_score(responses)
    assert score == 0.0, f"Expected 0.0 for unanimous panel, got {score}"


def test_five_agent_split_panel_triggers_disagreement():
    responses = [
        _mk_response("General Physician", "A"),
        _mk_response("Cardiologist", "A"),
        _mk_response("Neurologist", "B"),
        _mk_response("Pharmacologist", "B"),
        _mk_response("Evidence Reviewer", "C"),
    ]
    score = compute_disagreement_score(responses)
    assert score >= 0.5, f"Expected >= 0.5 for split panel, got {score}"


if __name__ == "__main__":
    test_identical_answers_have_zero_disagreement()
    test_completely_different_answers_have_high_disagreement()
    test_pairwise_overlap_symmetry()
    test_single_response_has_no_disagreement()
    test_mcq_identical_letter_answers_have_zero_disagreement()
    test_mcq_differing_letter_answers_have_high_disagreement()
    test_pubmedqa_identical_binary_decisions_have_zero_disagreement()
    test_five_agent_unanimous_panel_does_not_trigger_disagreement()
    test_five_agent_split_panel_triggers_disagreement()
    print("All debate unit tests passed successfully!")

