# MedTrustAI — RAG Addon (Phase 6 of the remaining 60%)

Implements: PDF Extraction → Text Chunking → Embeddings → ChromaDB →
Retrieval → injected into your existing 5-agent system.

Matches your architecture diagram exactly:
```
WHO/CDC/NIH/MedlinePlus PDFs
        -> Extract Text (PyMuPDF)
        -> Split into Chunks
        -> Generate Embeddings (Sentence Transformers - local & free)
        -> Store in ChromaDB
        -> User asks a question
        -> Retrieve relevant chunks
        -> Send chunks + question to the 5 agents
        -> Agents answer (grounded in retrieved evidence)
```

## What's new in this addon

```
MediHive/
├── rag/
│   ├── __init__.py
│   ├── pdf_extractor.py    # Step 1: PDF -> raw text
│   ├── chunker.py          # Step 2: text -> overlapping chunks
│   ├── vector_store.py     # Steps 3-4: embed + store in ChromaDB
│   ├── retriever.py        # Steps 5-6: question -> relevant chunks
│   └── ingest.py           # Runs the full pipeline end-to-end
├── data/
│   └── raw_pdfs/           # <- YOU put WHO/CDC/NIH PDFs here
├── app.py                  # UPDATED - now retrieves context before agents run
└── requirements_rag_addon.txt
```

**Your existing agents, memory, debate, and fusion code are UNCHANGED.**
`agent.run(question, context=...)` already accepted a `context` parameter
from day one — this addon is simply the first thing that actually fills
it in with real retrieved content instead of `None`.

---

## Setup

1. Copy the `rag/` folder into your existing `MediHive/rag/`
2. Replace your existing `app.py` with the updated one in this addon
3. Install new dependencies:
   ```powershell
   pip install -r requirements_rag_addon.txt
   ```
   (This installs PyMuPDF, sentence-transformers, and chromadb. The
   sentence-transformers install will also pull in PyTorch if you don't
   have it — this is a larger download, ~1-2 GB, be patient.)

---

## Getting sample PDFs (WHO / CDC / NIH-MedlinePlus)

You need to manually download a few real PDFs and place them in
`data/raw_pdfs/`. Here's where to get legitimate, free ones:

**WHO Fact Sheets** (short, focused, good for testing):
- https://www.who.int/news-room/fact-sheets/detail/hypertension
- https://www.who.int/news-room/fact-sheets/detail/diabetes
- https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds)

On each page, use your browser's **Print → Save as PDF** (or look for a
"Download" / PDF icon on the page) to save it as a PDF into
`data/raw_pdfs/`.

**CDC guidance pages:**
- https://www.cdc.gov/heartdisease/index.htm
- https://www.cdc.gov/diabetes/basics/index.html

Same approach — Print → Save as PDF from the browser.

**NIH / MedlinePlus:**
- https://medlineplus.gov/heartdiseases.html
- https://medlineplus.gov/diabetes.html

Same approach.

Start with just **2-3 PDFs** to test the pipeline works, then add more
later — you don't need a huge library to demonstrate RAG is working.

---

## Run the ingestion pipeline

Once you have PDFs in `data/raw_pdfs/`:

```powershell
python rag/ingest.py
```

You'll see output like:
```
[1/3] Extracting text from PDFs in data/raw_pdfs/...
Extracting: hypertension.pdf
  -> Saved extracted text to data/extracted_text/hypertension.txt (4213 characters)

[2/3] Splitting extracted text into chunks...
hypertension.txt: split into 6 chunks
Total chunks across all documents: 6

[3/3] Generating embeddings and storing in ChromaDB...
Loading embedding model 'all-MiniLM-L6-v2' (first load may take a moment)...
Embedding 6 chunks...
Stored 6 chunks in ChromaDB collection 'medihive_knowledge_base'

INGESTION COMPLETE
Chunks stored this run : 6
Total chunks in index  : 6
```

This only needs to be re-run when you **add new PDFs** — it's safe to
run repeatedly (won't duplicate existing chunks).

---

## Verify it's working

1. Start (or restart) your server:
   ```powershell
   python -m uvicorn app:app --reload
   ```

2. Check the knowledge base status:
   ```
   http://127.0.0.1:8000/knowledge-base/status
   ```
   Should show `"chunks_indexed": 6` (or however many you ingested),
   `"rag_active": true`.

3. Ask a question related to what you ingested (e.g. if you ingested the
   hypertension fact sheet, ask about hypertension) via `/docs` → `/ask`.

4. In the response, check:
   - `"rag_used": true`
   - `"rag_sources"` — shows which document chunks were retrieved and
     used for this specific answer

If `rag_used` is `false`, either nothing has been ingested yet, or the
question didn't match any indexed content closely enough.

---

## Important notes for your report

- **Embeddings are 100% local and free** (Sentence Transformers,
  `all-MiniLM-L6-v2`) — no OpenAI billing involved, avoiding the issue
  you hit earlier in the project.
- **Backward compatible**: if `data/raw_pdfs/` is empty or ingestion
  hasn't been run, `/ask` behaves EXACTLY like your 40% build (agents
  answer from their own knowledge only). This means you can directly
  compare "with RAG" vs "without RAG" accuracy using your existing
  PubMedQA/MedQA evaluation scripts — just run them once before
  ingesting any PDFs, and once after, and compare the numbers.
- **Chunking strategy**: fixed-size character chunks (800 chars, 150
  overlap) rather than sentence-aware splitting — simple and effective
  for this project scope; a documented design choice, not a limitation
  you need to fix unless you want to go further.
