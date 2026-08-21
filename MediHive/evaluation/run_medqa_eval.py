"""
evaluation/run_medqa_eval.py

Evaluates MediHive against MedQA (USMLE-style 4-option multiple choice
questions).

IMPORTANT: your MediHive server (`uvicorn app:app --reload`) must
already be running in another terminal before you run this script.

Usage:
    python evaluation/run_medqa_eval.py --limit 10
    python evaluation/run_medqa_eval.py --limit 100 --output evaluation/results/medqa_100

If the run is interrupted, run the EXACT SAME command again to resume.

Outputs:
    - <output>.csv           short summary per question
    - <output>_summary.json  aggregate accuracy + macro Precision/Recall/F1
                              + per-label breakdown
    - <output>_detail.json   full detail: question, all agents, fusion
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.eval_utils import EvalRunner, extract_mc_choice


def load_medqa(limit: int):
    from datasets import load_dataset

    print("Downloading/loading MedQA (USMLE 4-options)... this may take a minute the first time.")
    ds = load_dataset("GBaker/MedQA-USMLE-4-options", split="test")
    ds = ds.select(range(min(limit, len(ds))))
    return ds


def build_question_text(item) -> str:
    options = item["options"]
    options_text = "\n".join(f"{letter}) {text}" for letter, text in options.items())

    return (
        f"{item['question']}\n\n"
        f"Options:\n{options_text}\n\n"
        f"Answer with the single correct option letter and briefly justify why."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of questions to evaluate")
    parser.add_argument("--output", type=str, default="evaluation/results_medqa",
                         help="Base output path, no extension (e.g. evaluation/results_medqa)")
    parser.add_argument("--max-retries", type=int, default=2,
                         help="Retries per question on transient network errors")
    parser.add_argument("--retry-wait", type=int, default=15,
                         help="Seconds to wait between retries")
    args = parser.parse_args()

    output_base = args.output.replace(".csv", "")

    dataset = load_medqa(args.limit)
    runner = EvalRunner("MedQA", output_base, max_retries=args.max_retries, retry_wait=args.retry_wait)

    print(f"\nRunning {len(dataset)} MedQA questions against MediHive...\n")

    for i, item in enumerate(dataset, start=1):
        question_text = build_question_text(item)
        options = item["options"]
        ground_truth = item["answer_idx"]
        runner.run_one(i, len(dataset), question_text, ground_truth, extract_mc_choice, parse_args=(options,))

    summary = runner.summary()

    os.makedirs(os.path.dirname(output_base) or ".", exist_ok=True)

    csv_path = f"{output_base}.csv"
    all_fieldnames = []
    for row in runner.results:
        for key in row.keys():
            if key not in all_fieldnames:
                all_fieldnames.append(key)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames, restval="")
        writer.writeheader()
        for row in runner.results:
            writer.writerow(row)

    summary_path = f"{output_base}_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    runner.save_full_detail()

    print("\n" + "=" * 50)
    print("MEDQA EVALUATION SUMMARY")
    print("=" * 50)
    for k, v in summary.items():
        print(f"{k:32s}: {v}")
    print(f"\nShort summary CSV : {csv_path}")
    print(f"Aggregate summary : {summary_path}")
    print(f"Full detail (Q + all agents + fusion): {output_base}_detail.json")


if __name__ == "__main__":
    main()
