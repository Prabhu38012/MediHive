"""
rag/retriever.py

Phase 6 (RAG) - Steps 5 & 6: User asks a question -> Retrieve relevant
document chunks.

This is what app.py calls before running the 5 agents. It takes the raw
question, embeds it with the SAME model used to embed the documents,
and finds the top-k most similar chunks from ChromaDB.
"""

from rag.vector_store import get_embedding_model, get_chroma_collection, collection_size

TOP_K = 4  # number of chunks to retrieve per question


def retrieve_context(question: str, top_k: int = TOP_K) -> str:
    """Given a question, return the top-k most relevant document chunks
    concatenated into a single context string, ready to inject into
    agent.run(question, context=...).

    Returns an empty string if no documents have been ingested yet -
    in that case, agents simply fall back to answering from their own
    knowledge (same as the 40% build), so this is safe to call even
    before any PDFs are ingested.
    """
    if collection_size() == 0:
        return ""

    model = get_embedding_model()
    collection = get_chroma_collection()

    query_embedding = model.encode([question], convert_to_numpy=True).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection_size()),
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return ""

    context_parts = []
    for doc_text, meta in zip(documents, metadatas):
        source = meta.get("source", "unknown source")
        context_parts.append(f"[Source: {source}]\n{doc_text}")

    return "\n\n---\n\n".join(context_parts)


def retrieve_context_with_sources(question: str, top_k: int = TOP_K) -> dict:
    """Same as retrieve_context, but also returns which sources were
    used - useful for showing citations in the API response or for
    debugging retrieval quality.
    """
    if collection_size() == 0:
        return {"context": "", "sources": []}

    model = get_embedding_model()
    collection = get_chroma_collection()

    query_embedding = model.encode([question], convert_to_numpy=True).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection_size()),
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    sources = [
        {"source": meta.get("source", "unknown"), "distance": round(dist, 4)}
        for meta, dist in zip(metadatas, distances)
    ]

    context = "\n\n---\n\n".join(
        f"[Source: {meta.get('source', 'unknown')}]\n{doc}"
        for doc, meta in zip(documents, metadatas)
    )

    return {"context": context, "sources": sources}
