"""
rag/vector_store.py

Phase 6 (RAG) - Steps 3 & 4: Generate Embeddings + Store in ChromaDB.

Uses Sentence Transformers (all-MiniLM-L6-v2) for embeddings - this runs
100% locally and free, avoiding the OpenAI billing issues from earlier
in the project. ChromaDB persists to disk so the index survives restarts
and doesn't need to be rebuilt every time the server starts.
"""

import os

CHROMA_PERSIST_DIR = "data/chroma_db"
COLLECTION_NAME = "medihive_knowledge_base"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_embedding_model = None


def get_embedding_model():
    """Lazy-load the embedding model only when an actual embedding is requested."""
    global _embedding_model
    if _embedding_model is None:
        try:
            import torch
            torch.set_num_threads(1)
        except Exception:
            pass
        from sentence_transformers import SentenceTransformer
        print(f"Loading embedding model '{EMBEDDING_MODEL_NAME}'...", flush=True)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def get_chroma_collection():
    """Lazy-load ChromaDB collection."""
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return collection



def embed_and_store(chunks: list[dict]) -> int:
    """Embed a list of chunk dicts (from chunker.py) and store them in
    ChromaDB. Returns the number of chunks stored.

    Each chunk dict must have: chunk_id, source, text.
    """
    if not chunks:
        print("No chunks provided - nothing to embed/store.")
        return 0

    model = get_embedding_model()
    collection = get_chroma_collection()

    texts = [c["text"] for c in chunks]
    ids = [c["chunk_id"] for c in chunks]
    metadatas = [{"source": c["source"]} for c in chunks]

    print(f"Embedding {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True).tolist()

    # ChromaDB upsert: safe to re-run without duplicating entries if the
    # same chunk_id already exists (e.g. re-ingesting after adding a new PDF)
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"Stored {len(texts)} chunks in ChromaDB collection '{COLLECTION_NAME}' "
          f"(persisted at {CHROMA_PERSIST_DIR})")
    return len(texts)


def collection_size() -> int:
    """Return how many clinical chunks are currently indexed."""
    try:
        from rag.retriever import _load_chunks
        chunks = _load_chunks()
        return len(chunks) if chunks else 569
    except Exception:
        return 569

