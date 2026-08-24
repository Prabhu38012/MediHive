import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import _extract_json
from evaluation.eval_utils import extract_mc_choice, extract_yes_no_maybe


def test_json_sanitization():
    # Test 1: Markdown code fence + unquoted letter
    raw1 = "```json\n{\n  \"answer\": A,\n  \"reasoning\": \"test reasoning\",\n  \"confidence\": 0.95\n}\n```"
    res1 = _extract_json(raw1)
    assert res1["answer"] == "A", f"Expected 'A', got {res1['answer']}"
    assert res1["confidence"] == 0.95, f"Expected 0.95, got {res1['confidence']}"

    # Test 2: Unquoted yes/no/maybe
    raw2 = "{\n  \"answer\": yes,\n  \"reasoning\": \"Evidence confirms hypothesis\",\n  \"confidence\": 0.9\n}"
    res2 = _extract_json(raw2)
    assert res2["answer"] == "yes", f"Expected 'yes', got {res2['answer']}"

    # Test 3: Multiple choice extractor
    options = {"A": "Option Alpha", "B": "Option Beta", "C": "Option Gamma", "D": "Option Delta"}
    assert extract_mc_choice("B", options) == "B"
    assert extract_mc_choice("Option B) Option Beta", options) == "B"
    assert extract_mc_choice('{"answer": "C"}', options) == "C"

    # Test 4: PubMedQA Yes/No/Maybe extractor
    assert extract_yes_no_maybe("yes") == "yes"
    assert extract_yes_no_maybe("The answer is maybe based on the text.") == "maybe"
    assert extract_yes_no_maybe('{"answer": "no"}') == "no"

    print("All JSON and evaluation extraction tests passed successfully!")


if __name__ == "__main__":
    test_json_sanitization()
