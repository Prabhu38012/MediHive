"""
app.py

Phase 1: Basic API entrypoint.
Phase 6 (RAG): retrieves relevant document context before running the 5
agents; falls back to normal (non-RAG) behavior if nothing is ingested.
Phase 7 (Iterative Fusion): consensus is now built via iterative
re-weighting (see fusion/consensus.py) instead of a single confidence
pick, and RAG-grounded answers get extra weight when context was used.

Full flow:
  Question -> Retrieve context (RAG) -> 5 agents (with context)
           -> shared memory -> debate if disagreement
           -> iterative fusion (weighs RAG-alignment + agreement) -> consensus

Run with:
    uvicorn app:app --reload
"""

import asyncio
import os
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.specialists import ALL_AGENTS
from memory.shared_memory import init_db, save_response, get_session_history
from debate.debate_engine import run_debate
from fusion.consensus import build_consensus
from rag.retriever import retrieve_context_with_sources
from rag.vector_store import collection_size

app = FastAPI(title="MedTrustAI Medical QA System", version="0.7.0")

# Enable CORS for all domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serves the legacy single-file HTML preview if present
if os.path.isdir("frontend"):
    app.mount("/ui", StaticFiles(directory="frontend", html=True), name="ui")


@app.on_event("startup")
def startup():
    init_db()


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    session_id: str
    question: str
    consensus_answer: str
    consensus_reasoning: str
    lead_agent: str
    preferred_option: str | None = None
    reasonable_alternative: str | None = None
    alternative_weight: float | None = 0.0
    average_confidence: float
    fusion_weighted_confidence: float
    fusion_weights: dict[str, float]
    debate_triggered: bool
    agent_breakdown: list[dict]
    rag_used: bool
    rag_sources: list[dict]


@app.get("/api/health")
@app.get("/api/status")
def health_status():
    return {
        "system": "MedTrustAI Medical QA System",
        "status": "ok",
        "phase": "70% implementation - multi-agent + shared memory + debate + RAG + iterative fusion",
        "knowledge_base_chunks": collection_size(),
    }


@app.post("/ask", response_model=QuestionResponse)
@app.post("/api/ask", response_model=QuestionResponse)
async def ask(request: QuestionRequest):
    session_id = str(uuid.uuid4())
    question = request.question

    # --- Phase 6: RAG retrieval (safe no-op if nothing has been ingested) ---
    retrieval = retrieve_context_with_sources(question)
    context = retrieval["context"]
    rag_used = bool(context)

    # --- Phase 3: run all 5 agents concurrently, with retrieved context ---
    loop = asyncio.get_running_loop()
    round1_responses = await asyncio.gather(
        *[loop.run_in_executor(None, agent.run, question, context) for agent in ALL_AGENTS]
    )


    # --- Phase 4: persist round 1 to shared memory ---
    for response in round1_responses:
        save_response(session_id, round_num=1, response=response)

    # --- Phase 5: debate if agents disagree ---
    final_responses, debate_triggered = run_debate(
        session_id=session_id,
        question=question,
        agents=ALL_AGENTS,
        round1_responses=list(round1_responses),
    )

    # --- Phase 7: iterative fusion (weighs agreement + RAG alignment) ---
    consensus = build_consensus(final_responses, debate_triggered, context=context)

    return QuestionResponse(
        session_id=session_id,
        question=question,
        rag_used=rag_used,
        rag_sources=retrieval["sources"],
        **consensus,
    )


@app.get("/memory/{session_id}")
@app.get("/api/memory/{session_id}")
def get_memory(session_id: str):
    """Inspect the full shared-memory trail for a session -
    useful for demos and for your project report/screenshots."""
    return {"session_id": session_id, "history": get_session_history(session_id)}


@app.get("/knowledge-base/status")
@app.get("/api/knowledge-base/status")
def knowledge_base_status():
    """Quick check: how many document chunks and PDFs are currently indexed."""
    import os
    count = collection_size()
    docs = []
    raw_dir = "data/raw_pdfs"
    if os.path.isdir(raw_dir):
        docs = sorted([f for f in os.listdir(raw_dir) if f.lower().endswith(".pdf")])
    return {
        "chunks_indexed": count,
        "rag_active": count > 0,
        "documents_count": len(docs),
        "documents": docs,
        "message": (
            "Knowledge base is empty - run `python rag/ingest.py` after adding "
            "PDFs to data/raw_pdfs/ to enable retrieval."
            if count == 0
            else f"{count} chunks indexed from {len(docs)} clinical documents and available for retrieval."
        ),
    }


# If the compiled React frontend exists, mount it at the root "/"
# StaticFiles with html=True will serve index.html for "/" and static assets
if os.path.isdir("static_react"):
    app.mount("/", StaticFiles(directory="static_react", html=True), name="react_ui")
else:
    @app.get("/")
    def fallback_root():
        return {
            "system": "MedTrustAI Medical QA System",
            "status": "ok",
            "phase": "70% implementation - multi-agent + shared memory + debate + RAG + iterative fusion",
            "knowledge_base_chunks": collection_size(),
            "frontend": "/ui",
        }

