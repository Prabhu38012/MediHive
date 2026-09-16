# 🏥 MedTrustAI — Medical Multi-Agent Engine (Backend)

The core AI engine powering **MedTrustAI**. This module provides a 5-specialist agent deliberation pipeline, Retrieval-Augmented Generation (RAG) over medical PDFs via ChromaDB, autonomous debate triggered on clinical disagreement, SQLite audit-trail memory, and iterative consensus fusion.

---

## 🏗️ Architecture & Pipeline Flow

```text
User Question
      │
      ▼
[ RAG Retriever ] ──> Query ChromaDB for medical guidelines & literature
      │
      ▼
[ 5 Specialist Agents ] ──> General Physician, Cardiologist, Neurologist,
      │                     Pharmacologist, Evidence Reviewer (Concurrent)
      ▼
[ Shared Memory (SQLite) ] ──> Log Round 1 proposals + confidence + reasoning
      │
      ▼
[ Debate Engine ] ──> Check inter-agent disagreement threshold (Jaccard / dissimilarity)
      │               ├── If High: Trigger Round 2 revision debate
      │               └── If Low: Proceed directly
      ▼
[ Iterative Fusion ] ──> Dynamic re-weighting (RAG alignment + agreement + confidence)
      │
      ▼
Final Consensus Response + Full Explainability Breakdown
```

---

## 🚀 Setup & Execution

### 1. Virtual Environment & Dependencies

```bash
cd MediHive
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
pip install -r requirements_rag_addon.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure your settings:

```ini
LLM_PROVIDER=gemini # or 'groq'

# If using Google Gemini (100% Free & 1M tokens/min):
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.7-flash

# If using Groq Cloud (Free API tier):
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

### 3. Ingesting Medical Documents (RAG)

Place your medical PDFs into the `data/` folder and run the ingestion pipeline:

```bash
python -m rag.ingest --pdf data/clinical_guidelines.pdf
```

### 4. Run the API Server

```bash
python -m uvicorn app:app --reload --port 8000
```

- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Built-in Static UI**: [http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui)

---

## 📡 API Endpoints

- `POST /ask` — Main medical consultation endpoint. Runs RAG -> 5 agents -> Debate -> Consensus.
- `GET /memory/{session_id}` — Retrieve full audit log and reasoning trail for a session.
- `GET /` — Health status, active features, and indexed knowledge-base statistics.

---

## 📊 Evaluation & Testing

Run unit tests:
```bash
pytest evaluation/test_debate.py -v
```

Run clinical benchmark evaluations:
```bash
# Evaluate on MedQA benchmark
python evaluation/run_medqa_eval.py --samples 50

# Evaluate on PubMedQA benchmark
python evaluation/run_pubmedqa_eval.py --samples 50
```
