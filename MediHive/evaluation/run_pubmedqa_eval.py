"""
evaluation/run_pubmedqa_eval.py

Evaluates MediHive against PubMedQA (labeled subset).

IMPORTANT: your MediHive server (`uvicorn app:app --reload`) must
already be running in another terminal before you run this script.

Usage:
    python evaluation/run_pubmedqa_eval.py --limit 10
    python evaluation/run_pubmedqa_eval.py --limit 100 --output evaluation/results/pubmedqa_100

If the run is interrupted (crash, network timeout, closed terminal),
just run the EXACT SAME command again - it will detect the existing
progress file and resume from where it left off instead of starting
over.

Outputs (using --output as the base name, no extension needed):
    - <output>.csv           short summary per question
    - <output>_summary.json  aggregate accuracy + macro Precision/Recall/F1
                              + per-label breakdown
    - <output>_detail.json   full detail: question, all agents, fusion
                              (this file is what enables resuming)
"""

import argparse
import csv
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.eval_utils import EvalRunner, extract_yes_no_maybe


def load_pubmedqa(limit: int):
    from datasets import load_dataset

    print("Downloading/loading PubMedQA (pqa_labeled)... this may take a minute the first time.")
    ds = load_dataset("qiaojin/PubMedQA", "pqa_labeled", split="train", token=os.getenv("HF_TOKEN"))
    ds = ds.select(range(min(limit, len(ds))))
    return ds


FEW_SHOT_COT_PUBMEDQA = """
[EXEMPLAR 1]
Abstract: We tested whether early metformin reduces 5-year diabetes incidence in prediabetic patients. The cumulative incidence was 14.3% with metformin vs 28.6% with placebo (p < 0.001).
Question: Does early metformin intervention reduce diabetes incidence in prediabetes?
Reasoning: The trial showed a statistically significant 50% relative risk reduction (p < 0.001) in diabetes incidence with metformin.
Answer: yes

[EXEMPLAR 2]
Abstract: High-dose Vitamin C was tested in septic shock for 28-day mortality vs standard care. Mortality was 34.8% in Vitamin C vs 35.1% in control (p = 0.95).
Question: Does intravenous vitamin C improve survival in septic shock?
Reasoning: Mortality differences were non-significant (p = 0.95), showing no survival benefit.
Answer: no
"""



def build_question_text(item, setting: str = "few_shot_cot") -> str:
    contexts = item.get("context", {})
    abstract_parts = contexts.get("contexts", []) if isinstance(contexts, dict) else []
    abstract_text = " ".join(abstract_parts)

    target = (
        f"[TARGET RESEARCH STUDY]\n"
        f"Abstract:\n{abstract_text}\n\n"
        f"Question: {item['question']}\n\n"
        f"Provide your evidence-based chain-of-thought reasoning and conclude strictly with one word: yes, no, or maybe."
    )

    if setting == "few_shot_cot":
        return f"{FEW_SHOT_COT_PUBMEDQA.strip()}\n\n{target}"
    elif setting == "zero_shot":
        return (
            f"Abstract:\n{abstract_text}\n\n"
            f"Question: {item['question']}\n\n"
            f"Answer strictly with one word: yes, no, or maybe."
        )
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of questions to evaluate")
    parser.add_argument("--setting", type=str, default="few_shot_cot",
                        choices=["few_shot_cot", "zero_shot_cot", "zero_shot"],
                        help="Benchmark setting (matches paper baseline table)")
    parser.add_argument("--output", type=str, default="evaluation/results_pubmedqa",
                         help="Base output path, no extension (e.g. evaluation/results_pubmedqa)")
    parser.add_argument("--max-retries", type=int, default=2,
                         help="Retries per question on transient network errors")
    parser.add_argument("--retry-wait", type=int, default=15,
                         help="Seconds to wait between retries")
    args = parser.parse_args()

    output_base = args.output.replace(".csv", "")

    dataset = load_pubmedqa(args.limit)
    runner = EvalRunner("PubMedQA", output_base, max_retries=args.max_retries, retry_wait=args.retry_wait)

    print(f"\nRunning {len(dataset)} PubMedQA questions against MediHive [{args.setting}]...\n")

    for i, item in enumerate(dataset, start=1):
        question_text = build_question_text(item, setting=args.setting)
        ground_truth = item["final_decision"]
        runner.run_one(i, len(dataset), question_text, ground_truth, extract_yes_no_maybe)


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
    print("PUBMEDQA EVALUATION SUMMARY")
    print("=" * 50)
    for k, v in summary.items():
        print(f"{k:32s}: {v}")
    print(f"\nShort summary CSV : {csv_path}")
    print(f"Aggregate summary : {summary_path}")
    print(f"Full detail (Q + all agents + fusion): {output_base}_detail.json")


if __name__ == "__main__":
    main()
