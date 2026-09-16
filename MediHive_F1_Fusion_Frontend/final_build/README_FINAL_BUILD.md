# MedTrustAI — F1 Score + Iterative Fusion + Frontend

Three additions in this package, all building on your existing RAG-enabled project.

## What's changed

```
MediHive/
├── evaluation/
│   ├── eval_utils.py           <- REPLACE: adds macro Precision/Recall/F1
│   ├── run_pubmedqa_eval.py    <- REPLACE (works automatically with new metrics)
│   └── run_medqa_eval.py       <- REPLACE (works automatically with new metrics)
│
├── fusion/
│   └── consensus.py            <- REPLACE: iterative fusion (was single confidence-pick)
│
├── app.py                      <- REPLACE: wires iterative fusion + serves frontend
│
└── frontend/                   <- NEW FOLDER
    └── index.html              <- the UI, served at http://127.0.0.1:8000/ui
```

No new pip installs needed — everything uses packages you already have
(FastAPI's `StaticFiles` ships with FastAPI itself).

---

## 1. F1 Score

`evaluation/eval_utils.py` now computes **macro-averaged Precision,
Recall, and F1** alongside accuracy — matching the "Accuracy, F1 Score"
box in your architecture diagram. No sklearn dependency; computed
manually so nothing new to install.

Your existing eval commands work exactly the same:
```powershell
python evaluation/run_pubmedqa_eval.py --limit 20
```

New fields now appear in `_summary.json`:
```json
{
  "accuracy": 0.75,
  "macro_precision": 0.71,
  "macro_recall": 0.68,
  "macro_f1": 0.69,
  "per_label_metrics": {
    "yes": {"precision": 0.8, "recall": 0.75, "f1": 0.77, "support": 8},
    "no": {"precision": 0.6, "recall": 0.6, "f1": 0.6, "support": 5},
    "maybe": {"precision": 0.7, "recall": 0.7, "f1": 0.7, "support": 7}
  },
  "rag_used_rate": 0.4
}
```

`rag_used_rate` is also new — tells you what fraction of eval questions
actually got RAG-grounded (useful once you've ingested more PDFs).

---

## 2. Iterative Fusion (upgrade)

**Old behavior:** pick whichever single agent had the highest stated
confidence. Done in one step.

**New behavior (`fusion/consensus.py`):** runs 3 rounds of re-weighting:
1. Start each agent's weight from its confidence, **plus a bonus if its
   reasoning overlaps with the retrieved RAG context** (grounded answers
   are trusted more than ungrounded guesses)
2. Each round, agents that agree with the current group consensus gain
   relative weight; outliers lose weight
3. After 3 rounds, weights stabilize and the highest-weighted agent's
   answer becomes the consensus

This is a genuine "iterative" fusion process rather than a single pick,
and it's RAG-aware — exactly what your diagram implies by placing
Retrieved Context directly upstream of the multi-agent system.

New fields in every `/ask` response:
```json
{
  "fusion_weighted_confidence": 0.87,
  "fusion_weights": {
    "General Physician": 0.22,
    "Cardiologist": 0.24,
    "Neurologist": 0.18,
    "Pharmacologist": 0.19,
    "Evidence Reviewer": 0.17
  },
  "agent_breakdown": [
    {"agent": "...", "fusion_weight": 0.24, ...}
  ]
}
```

---

## 3. Frontend

A single-page UI at:
```
http://127.0.0.1:8000/ui
```

Shows:
- Knowledge base status (how many chunks are indexed)
- A textbox to ask a question
- The consensus answer + reasoning
- Badges: lead agent, debate triggered or not, RAG grounded or not,
  weighted confidence
- Retrieved RAG sources (if used)
- Every agent's individual answer, reasoning, confidence, and fusion
  weight, sorted by weight — with a visual weight bar

No build step, no npm — it's a single static HTML file served directly
by FastAPI via `StaticFiles`.

**Heads up:** since local inference still takes 1-3+ minutes for a full
`/ask` call, the UI shows a loading spinner and disables the button
during the request — don't click multiple times, just wait.

---

## Setup steps

1. Copy `evaluation/eval_utils.py`, `evaluation/run_pubmedqa_eval.py`,
   `evaluation/run_medqa_eval.py` into your `evaluation/` folder,
   overwriting the old versions
2. Copy `fusion/consensus.py` into your `fusion/` folder, overwriting
   the old version
3. Copy `app.py` into your project root, overwriting the old version
4. Copy the whole `frontend/` folder into your project root (new folder)
5. Restart your server:
   ```powershell
   python -m uvicorn app:app --reload
   ```
6. Confirm the version bumped — visit `http://127.0.0.1:8000/`:
   ```json
   "phase": "70% implementation - multi-agent + shared memory + debate + RAG + iterative fusion"
   ```
7. Open the frontend:
   ```
   http://127.0.0.1:8000/ui
   ```
8. Ask a question and watch the fusion weights + RAG sources render

---

## What's left after this

- Ingest more PDFs (WHO/CDC/PubMed Guidelines/ICMR) for a richer
  knowledge base
- Run PubMedQA/MedQA evals with RAG active and compare against your
  earlier "no RAG" baseline numbers — now with accuracy AND F1 to report
- Optionally add MedMCQA as a third evaluation dataset (same pattern as
  the other two eval scripts)
