"""
rag/chunker.py

Phase 6 (RAG) - Step 2: Split into Chunks.

Splits extracted document text into overlapping chunks small enough to
embed meaningfully and retrieve precisely. Overlap prevents a fact from
being awkwardly split across two chunks with no context in either.
"""

import os
import re

EXTRACTED_TEXT_DIR = "data/extracted_text"

CHUNK_SIZE = 800       # characters per chunk (roughly ~150-200 words)
CHUNK_OVERLAP = 150     # characters shared between consecutive chunks


def clean_text(text: str) -> str:
    """Light cleanup: collapse excess whitespace/newlines from PDF extraction."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by character count.
    Simple and dependency-free; good enough for a 40%->60% project step.
    A more advanced version could split on sentence boundaries instead.
    """
    text = clean_text(text)
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def chunk_all_documents(input_dir: str = EXTRACTED_TEXT_DIR) -> list[dict]:
    """Read every .txt file in input_dir and chunk it. Returns a list of
    dicts: {"chunk_id": ..., "source": filename, "text": chunk_text}
    ready to be embedded and stored.
    """
    if not os.path.isdir(input_dir):
        print(f"No directory found at {input_dir} - run pdf_extractor.py first.")
        return []

    txt_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".txt")]
    if not txt_files:
        print(f"No extracted .txt files found in {input_dir}. Run pdf_extractor.py first.")
        return []

    all_chunks = []
    for filename in txt_files:
        path = os.path.join(input_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text)
        print(f"{filename}: split into {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "chunk_id": f"{filename}::chunk_{i}",
                "source": filename,
                "text": chunk,
            })

    print(f"\nTotal chunks across all documents: {len(all_chunks)}")
    return all_chunks


if __name__ == "__main__":
    chunk_all_documents()
