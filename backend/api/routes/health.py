from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from backend.config import settings
from backend.rag.vector_store import get_collection_count, list_indexed_collections
from backend.rag.ingestor import ingest_all_documents

router = APIRouter(prefix="/api", tags=["system"])

_ingest_status: dict = {"running": False, "last_result": None}


class IngestResponse(BaseModel):
    status: str
    results: list[dict]


def _run_ingest():
    global _ingest_status
    _ingest_status["running"] = True
    try:
        results = ingest_all_documents()
        _ingest_status["last_result"] = results
    finally:
        _ingest_status["running"] = False


@router.get("/health")
async def health():
    return {"status": "ok", "model": settings.OPENAI_LLM_MODEL}


@router.get("/status")
async def status():
    """Return ingestion status for all documents."""
    indexed = set(list_indexed_collections())
    docs = []
    for doc in settings.DOCUMENT_REGISTRY:
        pdf_path = settings.DATA_DIR / doc["filename"]
        docs.append(
            {
                "filename": doc["filename"],
                "law_name_en": doc["law_name_en"],
                "priority": doc["priority"],
                "pdf_exists": pdf_path.exists(),
                "indexed": doc["collection"] in indexed,
                "chunk_count": get_collection_count(doc["collection"])
                if doc["collection"] in indexed
                else 0,
                "can_be_suppressed": doc.get("can_be_suppressed", False),
            }
        )
    return {
        "documents": docs,
        "ingest_running": _ingest_status["running"],
        "last_ingest_result": _ingest_status["last_result"],
    }


@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingest(background_tasks: BackgroundTasks):
    """Trigger full document ingestion in background."""
    if _ingest_status["running"]:
        return IngestResponse(status="already_running", results=[])
    background_tasks.add_task(_run_ingest)
    return IngestResponse(status="started", results=[])
