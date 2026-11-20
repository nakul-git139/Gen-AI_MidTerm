from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Union
import fitz  # PyMuPDF
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
DATA_DIR = BASE_DIR / "data"
DEFAULT_PDF_PATH = DATA_DIR / "novapay_global_hr_manual_50p.pdf"


def extract_pages_from_pdf(pdf_path: str | Path = DEFAULT_PDF_PATH) -> List[Dict[str, Any]]:
    """
    Extracts text from each page of the provided PDF using PyMuPDF.

    Requirements:
    - Verifies PDF exists.
    - Preserves 1-based page numbers.
    - Stores each page's extracted text separately.
    - Handles empty pages gracefully.
    - Ensures extracted text is non-empty overall.
    """
    pdf_file = Path(pdf_path)

    # 1. Verify PDF exists
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_file.resolve()}")

    if not pdf_file.is_file():
        raise ValueError(f"Target path is not a file: {pdf_file.resolve()}")

    print(f"[Ingest] Opening PDF: {pdf_file.name} ({pdf_file.stat().st_size} bytes)")

    doc = fitz.open(str(pdf_file))
    total_pages = len(doc)

    if total_pages == 0:
        doc.close()
        raise ValueError(f"PDF document is empty (0 pages): {pdf_file.resolve()}")

    pages_data: List[Dict[str, Any]] = []
    empty_pages: List[int] = []

    # 2. Extract text from each page preserving page numbers
    for page_idx in range(total_pages):
        page_num = page_idx + 1
        page = doc[page_idx]
        text = page.get_text("text").strip()

        if not text:
            empty_pages.append(page_num)
            print(f"[Ingest] Warning: Page {page_num} is empty.")
            continue

        pages_data.append({
            "page_number": page_num,
            "text": text,
            "char_count": len(text),
            "source": pdf_file.name,
        })

    doc.close()

    # 3. Validation
    if not pages_data:
        raise ValueError("Extraction failed: All pages in the PDF are empty.")

    print(f"[Ingest] Extracted {len(pages_data)} / {total_pages} pages with text.")
    if empty_pages:
        print(f"[Ingest] {len(empty_pages)} empty page(s) encountered: {empty_pages}")

    return pages_data


def chunk_extracted_pages(
    pages_data: List[Dict[str, Any]],
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> List[Dict[str, Any]]:
    """
    Splits extracted pages into overlapping chunks using RecursiveCharacterTextSplitter.

    Requirements:
    - Chunk size: 800 characters
    - Chunk overlap: 150 characters
    - Preserves original PDF page numbers in metadata
    - Assigns unique chunk IDs (e.g. doc_p01_c01)
    - Returns list of chunks with: chunk_id, page_number, text, and source
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks: List[Dict[str, Any]] = []

    for page in pages_data:
        page_num = page["page_number"]
        page_text = page["text"]
        source = page.get("source", "novapay_global_hr_manual_50p.pdf")

        raw_chunks = splitter.split_text(page_text)
        for idx, chunk_text in enumerate(raw_chunks):
            chunk_id = f"doc_p{page_num:02d}_c{idx+1:02d}"
            chunks.append({
                "chunk_id": chunk_id,
                "page_number": page_num,
                "text": chunk_text,
                "source": source,
                "char_count": len(chunk_text),
            })

    print(f"[Ingest] Created {len(chunks)} chunks from {len(pages_data)} pages.")
    return chunks


def get_chunks_from_pdf(
    pdf_path: str | Path = DEFAULT_PDF_PATH,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> List[Dict[str, Any]]:
    """
    Convenience function to extract pages and chunk them in one step.
    """
    pages = extract_pages_from_pdf(pdf_path)
    return chunk_extracted_pages(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def validate_ingestion(pdf_path: str | Path = DEFAULT_PDF_PATH) -> bool:
    """
    Runs full verification for PDF ingestion and chunking.
    """
    try:
        pages = extract_pages_from_pdf(pdf_path)
        assert len(pages) > 0, "No pages extracted"
        assert all("page_number" in p and "text" in p for p in pages), "Missing page metadata"
        assert all(len(p["text"]) > 0 for p in pages), "Empty text found in extracted pages"

        chunks = chunk_extracted_pages(pages)
        assert len(chunks) > 0, "No chunks generated"
        assert all("chunk_id" in c and "page_number" in c and "text" in c for c in chunks), "Chunk missing required keys"

        print(f"[Ingest] Ingestion validation PASSED. Total valid pages: {len(pages)}, chunks: {len(chunks)}")
        print(f"[Ingest] Sample Chunk ID: {chunks[0]['chunk_id']} (Page {chunks[0]['page_number']}):")
        print("---" * 15)
        print(chunks[0]["text"][:200] + "...")
        print("---" * 15)
        return True
    except Exception as e:
        print(f"[Ingest] Ingestion validation FAILED: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF_PATH
    success = validate_ingestion(target)
    sys.exit(0 if success else 1)
