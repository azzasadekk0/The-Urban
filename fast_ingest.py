"""
fast_ingest.py -- Turbo ingestion: PyMuPDF for text PDFs, batched GPT-4o Vision for scanned.
Key optimisation: renders 5 pages into one image per Vision call (5x fewer API calls).

Usage:  python fast_ingest.py
"""
import os, sys, time, base64, hashlib, io
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_TRACING"]    = "false"
os.environ["LANGSMITH_API_KEY"]    = ""
os.environ["PYTHONIOENCODING"]     = "utf-8"

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from openai import OpenAI
import fitz                        # PyMuPDF

from backend.config import settings
from backend.rag.vector_store import get_or_create_collection
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── Config ────────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 1200
CHUNK_OVERLAP = 100
EMBED_BATCH   = 500
MAX_WORKERS   = 3          # parallel document threads
DPI           = 120        # lower DPI = smaller images = faster + cheaper
PAGES_PER_CALL = 5         # stitch N pages into one Vision call (5x speed boost)

client = OpenAI(api_key=settings.OPENAI_API_KEY)
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ".", "،", "؛", " "],
)


# ── Scanned Detection ─────────────────────────────────────────────────────────

def is_scanned(pdf_path: Path, sample: int = 3) -> bool:
    doc = fitz.open(str(pdf_path))
    chars = sum(len(doc[i].get_text("text").strip()) for i in range(min(sample, len(doc))))
    doc.close()
    return chars == 0


# ── Text PDF Extraction ───────────────────────────────────────────────────────

def extract_text_pages(pdf_path: Path) -> list[dict]:
    pages = []
    doc = fitz.open(str(pdf_path))
    for i, page in enumerate(doc):
        t = page.get_text("text").strip()
        if t:
            pages.append({"page": i + 1, "text": t})
    doc.close()
    return pages


# ── Vision OCR: Batched Page Stitching ───────────────────────────────────────

def render_pages_to_base64(doc: fitz.Document, page_indices: list[int], dpi: int) -> str:
    """Render multiple pages side-by-side into one base64 PNG (for batch Vision calls)."""
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pixmaps = [doc[i].get_pixmap(matrix=mat, alpha=False) for i in page_indices]

    # Stack vertically
    total_h = sum(p.height for p in pixmaps)
    max_w   = max(p.width  for p in pixmaps)

    combined = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, max_w, total_h))
    combined.set_rect(combined.irect, (255, 255, 255))   # white bg

    y = 0
    for pix in pixmaps:
        combined.copy(pix, fitz.IRect(0, y, pix.width, y + pix.height))
        y += pix.height

    return base64.b64encode(combined.tobytes("png")).decode("utf-8")


def ocr_batch_with_vision(b64_img: str, page_nums: list[int], law_name: str) -> str:
    """Send a batch image (multiple pages stacked) to GPT-4o Vision."""
    pages_str = ", ".join(str(p) for p in page_nums)
    prompt = (
        f"These are pages {pages_str} from the Egyptian legal/technical document '{law_name}', "
        "stacked top-to-bottom. Extract ALL Arabic text exactly as written, preserving "
        "article numbers, paragraph structure, and numbering. "
        "Separate each page with: --- PAGE BREAK ---\n"
        "Output only the extracted text — no explanations."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{b64_img}",
                    "detail": "high"
                }},
            ]}],
            max_tokens=4000,
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[OCR ERROR: {e}]"


def extract_scanned_pages(pdf_path: Path, doc_meta: dict, label: str) -> list[dict]:
    """Extract scanned PDF text using batched GPT-4o Vision (PAGES_PER_CALL pages per call)."""
    doc   = fitz.open(str(pdf_path))
    total = len(doc)
    pages = []

    # Build batches
    batches = [list(range(i, min(i + PAGES_PER_CALL, total)))
               for i in range(0, total, PAGES_PER_CALL)]
    total_batches = len(batches)

    print(f"  [{label}] SCANNED — {total} pages in {total_batches} batches "
          f"({PAGES_PER_CALL} pages/call) via GPT-4o Vision", flush=True)

    for b_idx, page_indices in enumerate(batches):
        b64   = render_pages_to_base64(doc, page_indices, DPI)
        text  = ocr_batch_with_vision(b64, [i + 1 for i in page_indices], doc_meta["law_name"])

        # Split result back into individual pages by PAGE BREAK marker
        parts = text.split("--- PAGE BREAK ---")
        for j, part in enumerate(parts):
            part = part.strip()
            page_num = page_indices[j] + 1 if j < len(page_indices) else page_indices[-1] + 1
            if part and not part.startswith("[OCR ERROR"):
                pages.append({"page": page_num, "text": part})

        pct = round((b_idx + 1) / total_batches * 100)
        print(f"  [{label}] Vision {pct:3d}%  (batch {b_idx+1}/{total_batches}, "
              f"pages {page_indices[0]+1}-{page_indices[-1]+1})", flush=True)

    doc.close()
    return pages


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_pages(pages: list[dict], doc_meta: dict) -> list[dict]:
    chunks = []
    for page in pages:
        for i, split in enumerate(splitter.split_text(page["text"])):
            if not split.strip():
                continue
            uid = hashlib.md5(
                f"{doc_meta['collection']}_{page['page']}_{i}_{split[:40]}".encode()
            ).hexdigest()
            chunks.append({
                "id": uid, "text": split,
                "metadata": {
                    "source_doc": doc_meta["filename"],
                    "collection": doc_meta["collection"],
                    "law_name":   doc_meta["law_name"],
                    "law_name_en": doc_meta["law_name_en"],
                    "priority":   doc_meta["priority"],
                    "can_be_suppressed": doc_meta.get("can_be_suppressed", False),
                    "page": page["page"], "chunk_index": i,
                },
            })
    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_and_store(chunks: list[dict], collection_name: str, label: str) -> int:
    if not chunks:
        return 0

    embedder   = OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL,
                                  openai_api_key=settings.OPENAI_API_KEY)
    collection = get_or_create_collection(collection_name)
    existing   = set(collection.get()["ids"]) if collection.count() > 0 else set()
    new        = [c for c in chunks if c["id"] not in existing]

    if not new:
        print(f"  [{label}] Already up-to-date.", flush=True)
        return 0

    texts, ids, metas = ([c["text"] for c in new],
                         [c["id"]   for c in new],
                         [c["metadata"] for c in new])
    added = 0
    for i in range(0, len(texts), EMBED_BATCH):
        bt, bi, bm = texts[i:i+EMBED_BATCH], ids[i:i+EMBED_BATCH], metas[i:i+EMBED_BATCH]
        collection.add(ids=bi, embeddings=embedder.embed_documents(bt), documents=bt, metadatas=bm)
        added += len(bt)
        print(f"  [{label}] Embedding {round((i+len(bt))/len(texts)*100)}%"
              f"  ({i+len(bt)}/{len(texts)})", flush=True)
    return added


# ── Per-Document Pipeline ─────────────────────────────────────────────────────

def ingest_one(doc_meta: dict) -> dict:
    label    = doc_meta["law_name_en"]
    pdf_path = settings.DATA_DIR / doc_meta["filename"]

    if not pdf_path.exists():
        print(f"  [{label}] MISSING — skipped.", flush=True)
        return {"status": "missing", "filename": doc_meta["filename"], "added": 0, "seconds": 0}

    t0      = time.time()
    scanned = is_scanned(pdf_path)

    if scanned:
        pages = extract_scanned_pages(pdf_path, doc_meta, label)
    else:
        print(f"  [{label}] Text PDF — PyMuPDF...", flush=True)
        pages = extract_text_pages(pdf_path)
        print(f"  [{label}] {len(pages)} pages.", flush=True)

    chunks = chunk_pages(pages, doc_meta)
    print(f"  [{label}] {len(chunks)} chunks → embedding...", flush=True)
    added   = embed_and_store(chunks, doc_meta["collection"], label)

    elapsed = round(time.time() - t0, 1)
    print(f"  [{label}] DONE +{added} chunks in {elapsed}s", flush=True)
    return {"status": "success", "filename": doc_meta["filename"],
            "added": added, "seconds": elapsed, "scanned": scanned}


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    # Only process documents not yet fully indexed
    from backend.rag.vector_store import get_collection_count, list_indexed_collections
    indexed = set(list_indexed_collections())

    pending = []
    skipped = []
    for doc in settings.DOCUMENT_REGISTRY:
        count = get_collection_count(doc["collection"]) if doc["collection"] in indexed else 0
        if count == 0:
            pending.append(doc)
        else:
            skipped.append((doc["law_name_en"], count))

    print("=" * 65)
    print("  The Urban -- Turbo Ingestion")
    print(f"  Pages/Vision call: {PAGES_PER_CALL} | Batch: {EMBED_BATCH} | Workers: {MAX_WORKERS}")
    print("=" * 65)
    for name, count in skipped:
        print(f"  [SKIP] Already indexed: {name} ({count} chunks)")
    print(f"\n  Processing {len(pending)} documents...", flush=True)
    print("=" * 65, flush=True)

    if not pending:
        print("  All documents already indexed!")
        return

    t_start = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(ingest_one, doc): doc["filename"] for doc in pending}
        for f in as_completed(futures):
            results.append(f.result())

    elapsed     = round(time.time() - t_start, 1)
    total_added = sum(r.get("added", 0) for r in results)

    print("\n" + "=" * 65)
    print(f"  DONE in {elapsed}s  |  +{total_added} new chunks")
    print("=" * 65)
    for r in sorted(results, key=lambda x: -x.get("seconds", 0)):
        tag = " [Vision OCR]" if r.get("scanned") else ""
        print(f"  {r['filename']:45s}  +{r.get('added',0):4d} chunks  {r.get('seconds',0)}s{tag}")


if __name__ == "__main__":
    main()
