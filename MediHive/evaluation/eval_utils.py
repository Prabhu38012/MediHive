"""
evaluation/eval_utils.py

Shared helpers for benchmark evaluation scripts (PubMedQA, MedQA).
Not used by the main app - standalone testing harness that calls your
running FastAPI server (POST /ask) and grades the responses.

v4: adds macro-averaged Precision / Recall / F1 alongside accuracy,
matching the "Accuracy, F1 Score" evaluation box in the architecture
diagram. Computed manually (no sklearn dependency) so this module has
no extra install requirements beyond what you already have.

Retains from v3: retry logic, incremental saving, resume capability,
per-label accuracy breakdown.
"""

import re
import time
import json
import os
import requests

API_URL = "http://127.0.0.1:8000/ask"

RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


def call_medihive(question_text: str, timeout: int = 900) -> dict:
    resp = requests.post(API_URL, json={"question": question_text}, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def call_medihive_with_retry(question_text: str, max_retries: int = 5, retry_wait: int = 10, timeout: int = 900) -> dict:
    last_error = None
    for attempt in range(1, max_retries + 2):
        try:
            return call_medihive(question_text, timeout=timeout)
        except RETRYABLE_EXCEPTIONS as e:
            last_error = e
            if attempt <= max_retries:
                print(f"  -> transient error ({type(e).__name__}), retrying in {retry_wait}s "
                      f"(attempt {attempt}/{max_retries})...", flush=True)
                time.sleep(retry_wait)
            else:
                break
        except requests.exceptions.HTTPError as e:
            last_error = e
            if attempt <= max_retries:
                print(f"  -> server error ({e}), retrying in {retry_wait}s "
                      f"(attempt {attempt}/{max_retries})...", flush=True)
                time.sleep(retry_wait)
            else:
                break
    raise last_error


def extract_yes_no_maybe(text: str) -> str | None:
    if not text:
        return None
    text_clean = text.strip().lower().strip("\"'.,;:")
    # Direct match
    if text_clean in {"yes", "no", "maybe"}:
        return text_clean

    # JSON or embedded regex check
    match = re.search(r'"answer"\s*:\s*"?\b(maybe|yes|no)\b', text, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    # Priority search in whole text
    for label in ["maybe", "yes", "no"]:
        if re.search(rf"\b{label}\b", text.lower()):
            return label
    return None


def extract_mc_choice(text: str, options: dict) -> str | None:
    if not text:
        return None

    valid_letters = set(k.upper() for k in options.keys())
    text_clean = text.strip().strip("\"'.,;:").upper()

    # 1. Exact letter match (e.g. "C" or "B")
    if text_clean in valid_letters:
        return text_clean

    # 2. Leading letter match (e.g. "C) ...", "C: ...", "C. ...")
    m_lead = re.match(r'^\s*([A-Da-d])[\s\)\.\:\,\-]', text)
    if m_lead and m_lead.group(1).upper() in valid_letters:
        return m_lead.group(1).upper()

    # 3. JSON answer field
    match = re.search(r'"answer"\s*:\s*"?\b([A-Da-d])\b', text)
    if match and match.group(1).upper() in valid_letters:
        return match.group(1).upper()

    # 4. Explicit phrases (e.g. "Option C", "Choice C", "Answer: C", "corresponds to option C")
    m_explicit = re.search(r'(?:option|choice|answer|corresponds to option|select)[\s\:\-\*]*\b([A-Da-d])\b', text, re.IGNORECASE)
    if m_explicit and m_explicit.group(1).upper() in valid_letters:
        return m_explicit.group(1).upper()

    # 5. Parenthesized letter (e.g. "(C)")
    m_paren = re.search(r'\(([A-Da-d])\)', text)
    if m_paren and m_paren.group(1).upper() in valid_letters:
        return m_paren.group(1).upper()

    # 6. Fallback: semantic token overlap against option descriptions
    def _tokenize(s):
        return set(w.lower().strip(".,;:!?\"'()[]{}") for w in s.split() if len(w) > 3)

    answer_tokens = _tokenize(text)
    if answer_tokens:
        best_letter, best_score = None, 0.0
        for letter, option_text in options.items():
            option_tokens = _tokenize(option_text)
            if not option_tokens:
                continue
            overlap = len(answer_tokens & option_tokens) / len(option_tokens)
            if overlap > best_score:
                best_score = overlap
                best_letter = letter.upper()
        if best_score > 0.4:
            return best_letter

    return None



def compute_prf1(results: list[dict]) -> dict:
    """Compute macro-averaged Precision, Recall, and F1 across all
    ground-truth labels seen in this run. Manual implementation (no
    sklearn) so this module stays dependency-light.

    Only rows with a non-None `predicted` value are used for per-label
    precision/recall (unparsed rows can't be attributed to a predicted
    class); they still count against recall for their true label.
    """
    labels = sorted({str(r["ground_truth"]) for r in results})
    per_label = {}

    for label in labels:
        tp = sum(1 for r in results if str(r.get("predicted")) == label and str(r["ground_truth"]) == label)
        fp = sum(1 for r in results if str(r.get("predicted")) == label and str(r["ground_truth"]) != label)
        fn = sum(1 for r in results if str(r.get("predicted")) != label and str(r["ground_truth"]) == label)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        per_label[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(1 for r in results if str(r["ground_truth"]) == label),
        }

    macro_precision = round(sum(v["precision"] for v in per_label.values()) / len(per_label), 4) if per_label else 0.0
    macro_recall = round(sum(v["recall"] for v in per_label.values()) / len(per_label), 4) if per_label else 0.0
    macro_f1 = round(sum(v["f1"] for v in per_label.values()) / len(per_label), 4) if per_label else 0.0

    return {
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_label": per_label,
    }


class EvalRunner:
    """Runs questions against the API, tracks accuracy + F1, retries
    transient failures, saves incrementally, and supports resuming an
    interrupted run.
    """

    def __init__(self, dataset_name: str, output_base: str, max_retries: int = 2, retry_wait: int = 15):
        self.dataset_name = dataset_name
        self.output_base = output_base
        self.max_retries = max_retries
        self.retry_wait = retry_wait

        self.detail_path = f"{output_base}_detail.json"
        self.results = []
        self.full_records = []
        self.completed_indices = set()

        self._load_existing_progress()

    def _load_existing_progress(self):
        if os.path.exists(self.detail_path):
            try:
                with open(self.detail_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                self.full_records = existing
                self.completed_indices = {r["index"] for r in existing if "error" not in r}
                if self.completed_indices:
                    print(f"[{self.dataset_name}] Resuming: found {len(self.completed_indices)} "
                          f"already-completed questions in {self.detail_path}, will skip them.\n")
            except (json.JSONDecodeError, KeyError):
                print(f"[{self.dataset_name}] Existing detail file was unreadable, starting fresh.\n")

        for r in self.full_records:
            if "error" not in r:
                self.results.append({
                    "index": r["index"],
                    "question": r["question_text"][:200],
                    "ground_truth": r["ground_truth"],
                    "predicted": r["predicted"],
                    "consensus_answer": r["consensus_answer"],
                    "debate_triggered": r["debate_triggered"],
                    "average_confidence": r["average_confidence"],
                    "correct": r["correct"],
                    "elapsed_sec": r["elapsed_sec"],
                    "session_id": r["session_id"],
                    "rag_used": r.get("rag_used"),
                })

    def is_done(self, index: int) -> bool:
        return index in self.completed_indices

    def run_one(self, index: int, total: int, question_text: str, ground_truth, parse_fn, parse_args=()):
        if self.is_done(index):
            print(f"[{self.dataset_name}] {index}/{total} - already completed, skipping.", flush=True)
            return

        start = time.time()
        print(f"[{self.dataset_name}] {index}/{total} - sending question...", flush=True)

        try:
            response = call_medihive_with_retry(question_text, max_retries=self.max_retries, retry_wait=self.retry_wait)
        except Exception as e:
            print(f"  -> FAILED after retries ({type(e).__name__}): {e}")
            self.results.append({
                "index": index,
                "ground_truth": ground_truth,
                "predicted": None,
                "correct": False,
                "error": str(e),
                "elapsed_sec": round(time.time() - start, 1),
            })
            self.full_records.append({
                "index": index,
                "question_text": question_text,
                "ground_truth": ground_truth,
                "error": str(e),
            })
            self._save_incremental()
            return

        consensus_answer = response.get("consensus_answer", "")
        consensus_reasoning = response.get("consensus_reasoning", "")
        agent_breakdown = response.get("agent_breakdown", [])
        combined_text = f"{consensus_answer} {consensus_reasoning}"

        predicted = parse_fn(consensus_answer, *parse_args)
        if predicted is None:
            predicted = parse_fn(combined_text, *parse_args)
        correct = (predicted is not None) and (
            str(predicted).strip().lower() == str(ground_truth).strip().lower()
        )
        elapsed = round(time.time() - start, 1)

        status = "CORRECT" if correct else ("UNPARSED" if predicted is None else "WRONG")
        print(f"  -> {status} | predicted={predicted} | ground_truth={ground_truth} | {elapsed}s", flush=True)

        self.results.append({
            "index": index,
            "question": question_text[:200],
            "ground_truth": ground_truth,
            "predicted": predicted,
            "consensus_answer": consensus_answer,
            "debate_triggered": response.get("debate_triggered"),
            "average_confidence": response.get("average_confidence"),
            "correct": correct,
            "elapsed_sec": elapsed,
            "session_id": response.get("session_id"),
            "rag_used": response.get("rag_used"),
        })

        self.full_records.append({
            "index": index,
            "session_id": response.get("session_id"),
            "question_text": question_text,
            "ground_truth": ground_truth,
            "predicted": predicted,
            "correct": correct,
            "debate_triggered": response.get("debate_triggered"),
            "average_confidence": response.get("average_confidence"),
            "lead_agent": response.get("lead_agent"),
            "consensus_answer": consensus_answer,
            "consensus_reasoning": consensus_reasoning,
            "agent_breakdown": agent_breakdown,
            "rag_used": response.get("rag_used"),
            "rag_sources": response.get("rag_sources"),
            "elapsed_sec": elapsed,
        })

        self.completed_indices.add(index)
        self._save_incremental()
        time.sleep(2.5)

    def _save_incremental(self):
        with open(self.detail_path, "w", encoding="utf-8") as f:
            json.dump(self.full_records, f, indent=2)

    def summary(self) -> dict:
        total = len(self.results)
        correct = sum(1 for r in self.results if r["correct"])
        unparsed = sum(1 for r in self.results if r.get("predicted") is None and "error" not in r)
        errors = sum(1 for r in self.results if "error" in r)
        accuracy = round(correct / total, 4) if total else 0.0

        by_label = {}
        for r in self.results:
            label = str(r.get("ground_truth"))
            if label not in by_label:
                by_label[label] = {"total": 0, "correct": 0}
            by_label[label]["total"] += 1
            if r.get("correct"):
                by_label[label]["correct"] += 1

        per_label_accuracy = {
            label: round(stats["correct"] / stats["total"], 4) if stats["total"] else 0.0
            for label, stats in by_label.items()
        }

        avg_elapsed = (
            round(sum(r.get("elapsed_sec", 0) for r in self.results) / total, 1) if total else 0.0
        )
        debate_rate = (
            round(sum(1 for r in self.results if r.get("debate_triggered")) / total, 4) if total else 0.0
        )
        rag_rate = (
            round(sum(1 for r in self.results if r.get("rag_used")) / total, 4) if total else 0.0
        )

        prf1 = compute_prf1(self.results)

        return {
            "dataset": self.dataset_name,
            "total_questions": total,
            "correct": correct,
            "wrong": total - correct - unparsed - errors,
            "unparsed": unparsed,
            "request_errors": errors,
            "accuracy": accuracy,
            "macro_precision": prf1["macro_precision"],
            "macro_recall": prf1["macro_recall"],
            "macro_f1": prf1["macro_f1"],
            "per_label_metrics": prf1["per_label"],
            "accuracy_by_ground_truth_label": per_label_accuracy,
            "debate_triggered_rate": debate_rate,
            "rag_used_rate": rag_rate,
            "avg_seconds_per_question": avg_elapsed,
        }

    def save_full_detail(self, path: str = None):
        path = path or self.detail_path
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.full_records, f, indent=2)
        print(f"Full per-question detail (questions + agent breakdown + fusion) saved to: {path}")
