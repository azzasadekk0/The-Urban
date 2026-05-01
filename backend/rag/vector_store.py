import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.config import settings

os.environ["ANONYMIZED_TELEMETRY"] = "false"
os.environ["CHROMA_TELEMETRY"] = "false"

_client = None


def get_chroma_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        settings.VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(settings.VECTOR_DB_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_or_create_collection(collection_name: str):
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def list_indexed_collections() -> list[str]:
    client = get_chroma_client()
    return [c.name for c in client.list_collections()]


def get_collection_count(collection_name: str) -> int:
    try:
        col = get_or_create_collection(collection_name)
        return col.count()
    except Exception:
        return 0


def delete_collection(collection_name: str) -> bool:
    try:
        client = get_chroma_client()
        client.delete_collection(collection_name)
        return True
    except Exception:
        return False
