from __future__ import annotations
import os
import sys
import re
import json
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import chromadb
from chromadb.api.models.Collection import Collection
from google import genai
from google.genai.errors import APIError

from ingest import get_chunks_from_pdf, DEFAULT_PDF_PATH

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
CHROMA_DIR = BASE_DIR / "chroma_db"
META_FILE = CHROMA_DIR / ".ingestion_meta.json"
CACHE_FILE = CHROMA_DIR / ".embeddings_cache.json"
COLLECTION_NAME = "hr_policy_documents"
EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_GEN_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")


def get_gemini_client() -> genai.Client:
    """
    Initializes and returns the official google-genai Client using the key from .env.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is not set or contains the default placeholder. "
            "Please configure a valid key in your .env file."
        )
    return genai.Client(api_key=api_key)


def compute_file_hash(file_path: Path) -> str:
    """Computes SHA256 checksum for change detection."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_embeddings_cache() -> Dict[str, List[float]]:
    """Loads cached embeddings from disk if available."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_embeddings_cache(cache: Dict[str, List[float]]):
    """Saves embeddings cache to disk."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"[RAG] Warning: Could not save embeddings cache: {e}")


def _extract_retry_delay(error_str: str) -> float:
    """Extracts recommended wait time from 429 quota error if present."""
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_str, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 2.0
    match_delay = re.search(r"'retryDelay':\s*'(\d+)s'", error_str)
    if match_delay:
        return float(match_delay.group(1)) + 2.0
    return 20.0


def generate_embeddings_for_chunks(
    chunks: List[Dict[str, Any]],
    client: Optional[genai.Client] = None,
    batch_size: int = 25,
    max_retries: int = 5
) -> List[List[float]]:
    """
    Generates embeddings for chunks with persistent caching and adaptive rate-limit backoff.
    """
    if client is None:
        client = get_gemini_client()

    cache = _load_embeddings_cache()
    missing_indices: List[int] = []
    missing_texts: List[str] = []

    embeddings_result: List[Optional[List[float]]] = [None] * len(chunks)

    # 1. Fill from cache where available
    for idx, c in enumerate(chunks):
        c_id = c["chunk_id"]
        text_hash = hashlib.md5(c["text"].encode("utf-8")).hexdigest()
        cache_key = f"{c_id}_{text_hash}"
        if cache_key in cache:
            embeddings_result[idx] = cache[cache_key]
        else:
            missing_indices.append(idx)
            missing_texts.append(c["text"])

    cached_count = len(chunks) - len(missing_indices)
    if cached_count > 0:
        print(f"[RAG] Found {cached_count}/{len(chunks)} embeddings in local cache.")

    if not missing_indices:
        return [emb for emb in embeddings_result if emb is not None]

    print(f"[RAG] Generating embeddings for {len(missing_indices)} remaining chunks...")

    # 2. Process missing in batches
    for b_start in range(0, len(missing_indices), batch_size):
        b_indices = missing_indices[b_start : b_start + batch_size]
        b_texts = missing_texts[b_start : b_start + batch_size]
        success = False
        last_error = None

        for attempt in range(max_retries):
            try:
                response = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=b_texts,
                )
                b_embeddings = [e.values for e in response.embeddings]

                for idx, emb in zip(b_indices, b_embeddings):
                    embeddings_result[idx] = emb
                    c_id = chunks[idx]["chunk_id"]
                    text_hash = hashlib.md5(chunks[idx]["text"].encode("utf-8")).hexdigest()
                    cache[f"{c_id}_{text_hash}"] = emb

                _save_embeddings_cache(cache)
                success = True
                print(f"[RAG] Embedded batch {b_start // batch_size + 1}/{(len(missing_indices) + batch_size - 1) // batch_size} ({len(b_texts)} chunks).")
                time.sleep(1.0)
                break
            except Exception as e:
                last_error = e
                err_msg = str(e)
                wait_sec = _extract_retry_delay(err_msg)
                print(f"[RAG] API rate limit / error in batch {b_start // batch_size + 1} (attempt {attempt+1}/{max_retries}): {e}")
                print(f"[RAG] Waiting {wait_sec:.1f}s before retry...")
                time.sleep(wait_sec)

        if not success:
            raise RuntimeError(f"Embedding failed after {max_retries} attempts: {last_error}")

    return [emb for emb in embeddings_result if emb is not None]


def get_chroma_client() -> chromadb.PersistentClient:
    """Returns persistent ChromaDB client."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def build_vector_store(
    pdf_path: Path = DEFAULT_PDF_PATH,
    force_rebuild: bool = False
) -> Collection:
    """
    Builds or loads the persistent ChromaDB collection for HR policy documents.
    - Avoids duplicate ingestion if the PDF is already processed and unchanged.
    - Automatically rebuilds if force_rebuild=True or source PDF checksum changes.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF not found at: {pdf_file.resolve()}")

    client = get_chroma_client()
    current_hash = compute_file_hash(pdf_file)

    # Check existing metadata
    stored_hash = None
    if META_FILE.exists() and not force_rebuild:
        try:
            with open(META_FILE, "r") as f:
                meta = json.load(f)
                stored_hash = meta.get("pdf_hash")
        except Exception:
            stored_hash = None

    # Check if collection exists
    existing_collections = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing_collections and not force_rebuild:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        if count > 0 and stored_hash == current_hash:
            print(f"[RAG] Collection '{COLLECTION_NAME}' is up to date ({count} chunks). Skipping re-ingestion.")
            return collection

    print(f"[RAG] Initializing collection '{COLLECTION_NAME}' (force_rebuild={force_rebuild})...")
    if COLLECTION_NAME in existing_collections:
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # 1. Chunk PDF
    chunks = get_chunks_from_pdf(pdf_file, chunk_size=800, chunk_overlap=150)
    print(f"[RAG] Preparing embeddings for {len(chunks)} chunks with '{EMBEDDING_MODEL}'...")

    # 2. Embeddings with caching & adaptive backoff
    embeddings = generate_embeddings_for_chunks(chunks)

    # 3. Store in ChromaDB
    ids = [c["chunk_id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [
        {
            "page_number": c["page_number"],
            "source": c["source"],
            "chunk_id": c["chunk_id"],
        }
        for c in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    # 4. Save metadata state for cache validation
    with open(META_FILE, "w") as f:
        json.dump(
            {
                "pdf_hash": current_hash,
                "pdf_file": str(pdf_file.name),
                "total_chunks": len(chunks),
                "embedding_model": EMBEDDING_MODEL,
                "timestamp": time.time(),
            },
            f,
            indent=2,
        )

    print(f"[RAG] Successfully stored {collection.count()} chunks in '{COLLECTION_NAME}'.")
    return collection


def retrieve(question: str, top_k: int = 7) -> List[Dict[str, Any]]:
    """
    Retrieves the top_k most relevant policy chunks for a given question.

    Requirements:
    - Generates embedding dynamically for ANY question.
    - Searches ChromaDB using vector similarity.
    - Returns relevant chunks including page numbers, chunk IDs, and text.
    """
    if not question.strip():
        return []

    client = get_chroma_client()
    collection = client.get_collection(COLLECTION_NAME)

    # 1. Embed query dynamically
    gemini_client = get_gemini_client()
    res = gemini_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=question.strip(),
    )
    query_embedding = res.embeddings[0].values

    # 2. Similarity search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    chunks: List[Dict[str, Any]] = []
    if results and "ids" in results and results["ids"]:
        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            document = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i] if "distances" in results and results["distances"] else None

            chunks.append({
                "chunk_id": chunk_id,
                "page_number": metadata.get("page_number"),
                "text": document,
                "source": metadata.get("source"),
                "distance": distance,
            })

    return chunks


def answer(question: str) -> dict:
    """
    Returns {"answer": <str>, "sources": [<page_or_chunk_id>, ...]}

    Workflow:
    1. Receive employee question.
    2. Generate question embedding dynamically using Gemini embedding model.
    3. Retrieve top 7 relevant chunks from existing ChromaDB collection.
    4. Pass retrieved text and question to Gemini Flash.
    5. Generate answer strictly from retrieved context (or '[not found]').
    6. Return answer and actual source references.
    """
    q_clean = question.strip()
    if not q_clean:
        return {"answer": "[not found]", "sources": []}

    # 1. Retrieve top 7 relevant chunks
    chunks = retrieve(q_clean, top_k=7)
    if not chunks:
        return {"answer": "[not found]", "sources": []}

    # 2. Format context strictly from retrieved chunks
    context_entries = []
    for c in chunks:
        context_entries.append(
            f"[Source: Page {c['page_number']}, {c['chunk_id']}]\n{c['text']}"
        )
    context_text = "\n\n---\n\n".join(context_entries)

    # 3. Formulate strict grounding prompt
    prompt = f"""You are the official NovaPay HR Policy Assistant.
Answer the employee's QUESTION strictly using ONLY the factual content in the RETRIEVED CONTEXT below.

GROUNDING RULES:
1. Base your answer ONLY on explicit facts, guidelines, numbers, and clauses in the RETRIEVED CONTEXT.
2. Synthesize and combine relevant information from multiple retrieved chunks when appropriate.
3. If the retrieved context contains relevant guidelines, procedures, or policy clauses on the topic, explain clearly and concisely what the handbook specifies.
4. If the retrieved context DOES NOT contain sufficient factual evidence to answer the question, or if the question asks about something completely absent/unrelated to the handbook (e.g., world capitals, trivia, external topics, unmentioned policies), you MUST return EXACTLY and ONLY:
[not found]
5. Do NOT use external knowledge, do NOT assume, and do NOT fabricate policy details, page numbers, or citations.

RETRIEVED CONTEXT:
{context_text}

QUESTION:
{q_clean}

ANSWER:"""

    # 4. Generate answer with fallback and retries
    client = get_gemini_client()
    raw_answer = ""
    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.1-flash-lite",
        DEFAULT_GEN_MODEL,
        "gemini-flash-latest",
    ]

    for attempt in range(3):
        for m in models_to_try:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=prompt,
                )
                if response and response.text:
                    raw_answer = response.text.strip()
                    break
            except Exception:
                continue
        if raw_answer:
            break
        time.sleep(2.0)

    if not raw_answer:
        raw_answer = "[not found]"

    # 5. Process answer and determine sources
    ans_lower = raw_answer.lower().strip()
    if ans_lower == "[not found]" or ans_lower.startswith("[not found]"):
        return {"answer": "[not found]", "sources": []}

    # Extract actual matching sources from retrieved chunks
    sources = []
    seen = set()
    for c in chunks:
        cid = c["chunk_id"]
        pnum = c["page_number"]
        src_str = f"Page {pnum}, {cid}"
        if cid in raw_answer or f"page {pnum}" in raw_answer.lower() or f"page: {pnum}" in raw_answer.lower():
            if src_str not in seen:
                seen.add(src_str)
                sources.append(src_str)

    # If the model didn't explicitly write the citations in text, cite the top chunks that provided context
    if not sources and chunks:
        for top_c in chunks[:3]:
            src_str = f"Page {top_c['page_number']}, {top_c['chunk_id']}"
            if src_str not in seen:
                seen.add(src_str)
                sources.append(src_str)

    return {"answer": raw_answer, "sources": sources}


def run_assessment_tests():
    """
    Executes the required assessment tests:
    - 2 initial verification questions
    - 5 assigned HR policy assessment questions
    """
    print("=" * 80)
    print("NOVA PAY HR POLICY ASSISTANT — PROMPT 3 EVALUATION")
    print("=" * 80)

    # Verify vector store is loaded without re-embedding
    build_vector_store()

    tests = [
        ("VERIFICATION TEST 1 (Policy in context)", "What is the policy for annual performance calibration and promotion cycles?"),
        ("VERIFICATION TEST 2 (Out-of-domain trivia)", "What is the capital of France?"),
        ("HR ASSESSMENT QUESTION 1 (ESOP)", "What is the ESOP vesting schedule and cliff period for Band-3 engineers?"),
        ("HR ASSESSMENT QUESTION 2 (Travel Reimbursement)", "What is the maximum daily reimbursement cap for hotel lodging in Tier-1 international cities, and which cities are covered?"),
        ("HR ASSESSMENT QUESTION 3 (Parental Leave)", "What are the parental and paternity leave entitlements and time limits to take them at NovaPay?"),
        ("HR ASSESSMENT QUESTION 4 (Archival / Performance)", "What are the standard procedural guidelines for archiving routine records associated with global employment grades and performance calibration?"),
        ("HR ASSESSMENT QUESTION 5 (Sabbatical & Exit)", "What are the standard procedural guidelines for archiving routine records regarding sabbatical eligibility, notice period buyouts, and exit clearances?"),
    ]

    for label, question in tests:
        print("\n" + "#" * 80)
        print(f"{label}")
        print("#" * 80)

        result = answer(question)
        grounding_status = "Grounded" if result["answer"] != "[not found]" else "Not Grounded (Not Found)"

        print(f"\nQUESTION:\n{question}\n")
        print(f"GENERATED ANSWER:\n{result['answer']}\n")
        print(f"SOURCES:\n{result['sources']}\n")
        print(f"GROUNDING STATUS:\n{grounding_status}")
        print("-" * 80)
        # Flush stdout so output is immediately visible
        sys.stdout.flush()
        time.sleep(2.0)


if __name__ == "__main__":
    run_assessment_tests()
