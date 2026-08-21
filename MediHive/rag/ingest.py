"""
rag/ingest.py

Phase 6 (RAG) - runs the FULL pipeline end-to-end:

    PDFs in data/raw_pdfs/
        -> Extract text (pdf_extractor.py)
        -> Split into chunks (chunker.py)
        -> Generate embeddings + store in ChromaDB (vector_store.py)

Run this ONCE after adding PDFs to data/raw_pdfs/, and again any time
you add new documents. It's safe to re-run - existing chunks are
upserted (updated in place), not duplicated.

Usage:
    python rag/ingest.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.pdf_extractor import extract_all_pdfs
from rag.chunker import chunk_all_documents
from rag.vector_store import embed_and_store, collection_size


def main():
    print("=" * 60)
    print("MediHive RAG Ingestion Pipeline")
    print("=" * 60)

    print("\n[1/3] Extracting text from PDFs in data/raw_pdfs/...")
    extracted_paths = extract_all_pdfs()
    if not extracted_paths:
        print("\nNo PDFs were extracted. Add PDF files to data/raw_pdfs/ and rerun this script.")
        print("See README_RAG.md for where to get sample WHO/CDC/NIH documents.")
        return

    print("\n[2/3] Splitting extracted text into chunks...")
    chunks = chunk_all_documents()
    if not chunks:
        print("\nNo chunks were produced - check that extraction actually found text.")
        return

    print("\n[3/3] Generating embeddings and storing in ChromaDB...")
    stored_count = embed_and_store(chunks)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Chunks stored this run : {stored_count}")
    print(f"Total chunks in index  : {collection_size()}")
    print("\nYour MediHive server will now use retrieved context automatically")
    print("on the next /ask request - no restart needed unless the server")
    print("was started before ChromaDB existed.")


if __name__ == "__main__":
    main()
