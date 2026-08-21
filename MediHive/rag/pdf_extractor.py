"""
rag/pdf_extractor.py

Phase 6 (RAG) - Step 1: PDF Extraction.

Extracts raw text from every PDF placed in data/raw_pdfs/ (e.g. WHO,
CDC, NIH/MedlinePlus guideline documents you download yourself).

Uses PyMuPDF (imported as `fitz`) - fast and handles most real-world
PDFs (including multi-column layouts) better than pure pdfplumber for
this kind of document.
"""

import os
import pymupdf as fitz  # PyMuPDF

RAW_PDF_DIR = "data/raw_pdfs"
EXTRACTED_TEXT_DIR = "data/extracted_text"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a single PDF file, page by page."""
    doc = fitz.open(pdf_path)
    pages_text = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():
            pages_text.append(text)
    doc.close()
    return "\n\n".join(pages_text)


def extract_all_pdfs(raw_dir: str = RAW_PDF_DIR, output_dir: str = EXTRACTED_TEXT_DIR) -> list[str]:
    """Extract text from every PDF in raw_dir, save each as a .txt file
    in output_dir (same base filename), and return the list of saved
    .txt paths.
    """
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.isdir(raw_dir):
        print(f"No directory found at {raw_dir} - nothing to extract.")
        return []

    pdf_files = [f for f in os.listdir(raw_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"No PDF files found in {raw_dir}. "
              f"Add WHO/CDC/NIH/MedlinePlus PDFs there before running ingest.")
        return []

    saved_paths = []
    for filename in pdf_files:
        pdf_path = os.path.join(raw_dir, filename)
        print(f"Extracting: {filename}")
        try:
            text = extract_text_from_pdf(pdf_path)
        except Exception as e:
            print(f"  -> FAILED to extract {filename}: {e}")
            continue

        if not text.strip():
            print(f"  -> WARNING: no extractable text found in {filename} "
                  f"(it may be a scanned/image-only PDF - OCR would be needed, not covered here).")
            continue

        base_name = os.path.splitext(filename)[0]
        out_path = os.path.join(output_dir, f"{base_name}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        saved_paths.append(out_path)
        print(f"  -> Saved extracted text to {out_path} ({len(text)} characters)")

    return saved_paths


if __name__ == "__main__":
    extract_all_pdfs()
