import re
import hashlib
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import settings
from backend.rag.vector_store import get_or_create_collection

# ── PDF Library Auto-Detection ────────────────────────────────────────────────
try:
    import fitz  # PyMuPDF
    _PDF_BACKEND = "pymupdf"
except ImportError:
    try:
        import pdfplumber
        _PDF_BACKEND = "pdfplumber"
    except ImportError:
        import pypdf
        _PDF_BACKEND = "pypdf"


# ── Arabic Text Normalization ─────────────────────────────────────────────────

def normalize_arabic(text: str) -> str:
    """Reshape and apply BiDi algorithm so Arabic text is stored correctly."""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


# ── PDF Extraction ────────────────────────────────────────────────────────────

def extract_pages(pdf_path: Path) -> list[dict]:
    """Extract text from every page. Auto-selects PyMuPDF → pdfplumber → pypdf."""
    pages = []

    if _PDF_BACKEND == "pymupdf":
        import fitz
        doc = fitz.open(str(pdf_path))
        for i, page in enumerate(doc):
            raw = page.get_text("text")
            if raw.strip():
                pages.append({"page": i + 1, "text": raw.strip()})
        doc.close()

    elif _PDF_BACKEND == "pdfplumber":
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                raw = page.extract_text() or ""
                if raw.strip():
                    pages.append({"page": i + 1, "text": raw.strip()})

    else:  # pypdf
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        for i, page in enumerate(reader.pages):
            raw = page.extract_text() or ""
            if raw.strip():
                pages.append({"page": i + 1, "text": raw.strip()})

    return pages


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_pages(pages: list[dict], doc_meta: dict) -> list[dict]:
    """Split pages into overlapping chunks, tagging each with metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", "،", " "],
    )
    chunks = []
    for page in pages:
        splits = splitter.split_text(page["text"])
        for i, split in enumerate(splits):
            uid = hashlib.md5(
                f"{doc_meta['collection']}_{page['page']}_{i}_{split[:40]}".encode()
            ).hexdigest()
            chunks.append(
                {
                    "id": uid,
                    "text": split,
                    "metadata": {
                        "source_doc": doc_meta["filename"],
                        "collection": doc_meta["collection"],
                        "law_name": doc_meta["law_name"],
                        "law_name_en": doc_meta["law_name_en"],
                        "priority": doc_meta["priority"],
                        "can_be_suppressed": doc_meta.get("can_be_suppressed", False),
                        "page": page["page"],
                        "chunk_index": i,
                    },
                }
            )
    return chunks


# ── Embedding & Storage ───────────────────────────────────────────────────────

def embed_and_store(chunks: list[dict], collection_name: str) -> int:
    """Embed chunks with OpenAI and upsert into ChromaDB. Returns new chunks added."""
    if not chunks:
        return 0

    embedder = OpenAIEmbeddings(
        model=settings.OPENAI_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    collection = get_or_create_collection(collection_name)

    # Avoid re-embedding already-stored chunks
    existing_ids = set(collection.get()["ids"]) if collection.count() > 0 else set()
    new_chunks = [c for c in chunks if c["id"] not in existing_ids]
    if not new_chunks:
        return 0

    texts = [c["text"] for c in new_chunks]
    ids = [c["id"] for c in new_chunks]
    metadatas = [c["metadata"] for c in new_chunks]

    # Batch to stay within OpenAI rate limits
    batch_size = 500  # OpenAI allows up to 2048; 500 is safe and 5x faster
    for i in range(0, len(texts), batch_size):
        b_texts = texts[i : i + batch_size]
        b_ids = ids[i : i + batch_size]
        b_meta = metadatas[i : i + batch_size]
        embeddings = embedder.embed_documents(b_texts)
        collection.add(ids=b_ids, embeddings=embeddings, documents=b_texts, metadatas=b_meta)

    return len(new_chunks)


# ── Public API ────────────────────────────────────────────────────────────────

def ingest_document(doc_meta: dict) -> dict:
    """Full pipeline for a single document: PDF → extract → chunk → embed → store."""
    pdf_path = settings.DATA_DIR / doc_meta["filename"]

    if not pdf_path.exists():
        return {"status": "missing", "filename": doc_meta["filename"], "chunks_added": 0}

    try:
        pages = extract_pages(pdf_path)
        chunks = chunk_pages(pages, doc_meta)
        added = embed_and_store(chunks, doc_meta["collection"])
        return {
            "status": "success",
            "filename": doc_meta["filename"],
            "pages": len(pages),
            "chunks_added": added,
        }
    except Exception as exc:
        return {"status": "error", "filename": doc_meta["filename"], "error": str(exc)}


def ingest_all_documents() -> list[dict]:
    """Ingest every document listed in the registry."""
    return [ingest_document(doc) for doc in settings.DOCUMENT_REGISTRY]
