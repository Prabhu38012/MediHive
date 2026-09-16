# 🏥 MedTrustAI — Multi-Agent Medical Diagnostic & QA Platform

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5+-646CFF.svg)](https://vitejs.dev/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**MedTrustAI** is an end-to-end multi-agent medical diagnostic and Question-Answering (QA) platform. It leverages a team of five specialized AI clinical agents, autonomous debate mechanism, Retrieval-Augmented Generation (RAG) over medical literature, auditable SQLite shared memory, and iterative consensus fusion to produce accurate, explainable, and grounded medical recommendations.

---

## 🏛️ System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    React Client (Vite)                      │
│                  http://localhost:5173                      │
└──────────────────────────────┬──────────────────────────────┘
                               │  REST API / JSON
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                Express.js Gateway / Proxy                   │
│                  http://localhost:5000                      │
└──────────────────────────────┬──────────────────────────────┘
                               │  Reverse Proxy (Axios)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend Engine                     │
│                  http://localhost:8000                      │
└──────┬───────────────────────┬───────────────────────┬──────┘
       │                       │                       │
       ▼                       ▼                       ▼
┌──────────────┐       ┌───────────────┐       ┌───────────────┐
│ RAG Pipeline │       │ 5 Specialist  │       │ Shared Memory │
│  (ChromaDB + │       │    Agents     │       │   (SQLite     │
│   PyMuPDF)   │       │ (Gemini/Groq) │       │ Audit Trail)  │
└──────┬───────┘       └───────┬───────┘       └───────┬───────┘
       │                       │                       │
       └───────────────────────┼───────────────────────┘
                               ▼
               ┌───────────────────────────────┐
               │    Autonomous Debate Engine   │
               │ (Triggers on Disagreement)   │
               └───────────────┬───────┬───────┘
                               ▼
               ┌───────────────────────────────┐
               │   Iterative Fusion Consensus  │
               │ (RAG Alignment + Conf-Weight) │
               └───────────────┬───────┬───────┘
                               ▼
                     Final Consensus Output
```

---

## ✨ Features Implemented

### 1. 🩺 5 Specialized Clinical Agents
- **General Physician**: Holistic, broad clinical differential diagnosis (Occam's razor).
- **Cardiologist**: Cardiovascular focus (coronary, hemodynamics, ECG, arrhythmias).
- **Neurologist**: Neurological evaluation (CNS/PNS, stroke, seizures, red-flag symptoms).
- **Pharmacologist**: Drug mechanisms, drug-drug interactions, contraindications, and dosing.
- **Evidence Reviewer**: Assesses evidence certainty, guidelines, and literature backing.

### 2. ⚔️ Multi-Agent Debate Engine
- Computes pairwise Jaccard & confidence dissimilarity across agents.
- When disagreement exceeds threshold (`DEBATE_DISAGREEMENT_THRESHOLD`), automatically orchestrates a revision round where each specialist critiques peer opinions before finalizing their assessment.

### 3. 📚 Medical RAG (Retrieval-Augmented Generation)
- **PDF Extraction**: Ingestion of medical papers, clinical guidelines, and manuals via `PyMuPDF`.
- **Text Chunking**: Configurable token chunking with semantic overlap.
- **Vector Store**: Powered by `ChromaDB` for high-speed similarity search and contextual grounding with cited sources.

### 4. ⚖️ Iterative Fusion Consensus
- Builds consensus using dynamic multi-factor re-weighting.
- Rewards consensus convergence, high confidence, and direct alignment with retrieved RAG context.

### 5. 🗄️ Auditable Shared Memory
- SQLite-backed append-only audit trail.
- Logs full session history, round 1 proposals, debate revisions, agent confidence scores, and reasoning for full clinical explainability.

### 6. 📊 Benchmark Evaluation Suite
- Built-in evaluation scripts and performance metrics on standard medical benchmarks:
  - **MedQA** (USMLE-style multiple choice clinical questions)
  - **PubMedQA** (Biomedical research question answering)

### 7. 💻 Full-Stack Interactive Web App (MERN-Style)
- **React Frontend**: Modern, dark-mode medical dashboard displaying live agent breakdowns, debate timeline, confidence gauges, and RAG document citations.
- **Express Proxy**: Middleware proxying frontend requests seamlessly to FastAPI.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend UI** | React 18, Vite, JavaScript (ES6+), Vanilla CSS (Design Tokens), Lucide Icons |
| **Middleware Proxy** | Node.js, Express.js, Axios, CORS |
| **Backend API** | Python 3.11+, FastAPI, Uvicorn, Pydantic, Asyncio |
| **LLM Orchestration** | Google Gemini (Free Tier) / Groq Cloud, Structured JSON Schemas |
| **Vector DB & RAG** | ChromaDB, PyMuPDF (`fitz`), Recursive Chunker |
| **Persistence / Memory** | SQLite (`shared_memory.py`) |
| **Testing & Evaluation**| Pytest, MedQA, PubMedQA evaluation pipeline |

---

## 📁 Repository Structure

```text
├── MediHive/                               # Core Python AI & Multi-Agent Backend
│   ├── app.py                              # FastAPI main application & API endpoints (/ask, /memory)
│   ├── agents/
│   │   ├── base_agent.py                   # MedicalAgent class with structured Pydantic schema
│   │   └── specialists.py                  # 5 Medical Specialists definition
│   ├── debate/
│   │   └── debate_engine.py                # Disagreement scoring & debate orchestrator
│   ├── fusion/
│   │   └── consensus.py                    # Iterative Fusion consensus algorithm
│   ├── memory/
│   │   └── shared_memory.py                # SQLite append-only audit trail
│   ├── rag/                                # Retrieval-Augmented Generation Engine
│   │   ├── pdf_extractor.py                # PDF document parsing via PyMuPDF
│   │   ├── chunker.py                      # Smart text chunking
│   │   ├── vector_store.py                 # ChromaDB vector store collection
│   │   ├── retriever.py                    # Semantic context retrieval + citation extraction
│   │   └── ingest.py                       # Knowledge base ingestion CLI
│   ├── evaluation/                         # Medical Benchmark Evaluation Suite
│   │   ├── run_medqa_eval.py               # MedQA benchmark evaluator
│   │   ├── run_pubmedqa_eval.py            # PubMedQA benchmark evaluator
│   │   ├── test_debate.py                  # Pytest unit tests for debate logic
│   │   └── results_*.json / .csv           # Evaluation results
│   ├── utils/
│   │   └── llm_client.py                   # LLM client (Gemini / Groq)
│   ├── requirements.txt                    # Core Python dependencies
│   └── requirements_rag_addon.txt          # RAG dependencies (ChromaDB, PyMuPDF)
│
├── medihive-frontend/                      # Full-stack Web Application
│   ├── client/                             # React (Vite) Frontend UI
│   │   ├── src/
│   │   │   ├── App.jsx                     # Dashboard UI
│   │   │   ├── index.css                   # Custom modern styling
│   │   │   └── main.jsx                    # React entry point
│   │   ├── package.json
│   │   └── vite.config.js
│   └── server/                             # Express.js Proxy & API Gateway
│       ├── server.js                       # Express proxy (Port 5000 -> Port 8000)
│       └── package.json
```

---

## ⚡ Quick Start Guide

### 1. Start the Python FastAPI Backend

```powershell
cd MediHive
.\venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
pip install -r requirements_rag_addon.txt

# Start backend server
python -m uvicorn app:app --reload
```
*Backend runs at `http://127.0.0.1:8000` (API Docs: `http://127.0.0.1:8000/docs`)*

---

### 2. Start the Express Gateway (Optional Proxy)

```powershell
cd medihive-frontend\server
npm install
node server.js
```
*Proxy server runs at `http://localhost:5000`*

---

### 3. Start the React Frontend Client

```powershell
cd medihive-frontend\client
npm install
npm run dev
```
*Frontend UI is accessible at `http://localhost:5173` (or `http://localhost:3000`)*

---

## 🧪 Running Benchmarks & Tests

Run unit tests:
```powershell
pytest evaluation/test_debate.py -v
```

Run MedQA benchmark evaluation:
```powershell
python evaluation/run_medqa_eval.py --samples 50
```

Run PubMedQA benchmark evaluation:
```powershell
python evaluation/run_pubmedqa_eval.py --samples 50
```
