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


def _clean_query(question: str) -> str:
    """Extract only the target query if few-shot exemplars are present in the prompt."""
    if "[TARGET" in question:
        parts = question.split("[TARGET")
        return parts[-1][:1000]
    return question[:1000]


def retrieve_context(question: str, top_k: int = TOP_K) -> str:
    if collection_size() == 0:
        return ""

    model = get_embedding_model()
    collection = get_chroma_collection()

    clean_q = _clean_query(question)
    query_embedding = model.encode([clean_q], convert_to_numpy=True).tolist()

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
    if collection_size() == 0:
        return {"context": "", "sources": []}

    model = get_embedding_model()
    collection = get_chroma_collection()

    clean_q = _clean_query(question)
    query_embedding = model.encode([clean_q], convert_to_numpy=True).tolist()

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
