from langchain_openai import OpenAIEmbeddings
from backend.config import settings
from backend.rag.vector_store import get_or_create_collection, list_indexed_collections

# Topic Keywords (Arabic + English) 
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "height": ["ارتفاع", "طابق", "دور", "height", "floor", "storey", "طوابق"],
    "setback": ["تراجع", "ارتداد", "إرتداد", "setback", "حد البناء", "خط التنظيم"],
    "parking": ["موقف", "جراج", "مواقف", "parking", "garage", "سيارة", "سيارات"],
    "fire": ["حريق", "إطفاء", "fire", "evacuation", "إخلاء", "دهليز", "سلم هروب"],
    "area": ["مساحة", "نسبة البناء", "coverage", "built area", "مبني", "البناء"],
    "violation": ["مخالفة", "تصالح", "violation", "reconciliation", "مخالفات"],
    "new_city": ["مدينة جديدة", "هيئة المجتمعات", "new city", "NUCA", "مجتمعات عمرانية"],
    "old_city": ["محافظة", "بلدية", "municipality", "old city", "حضري قديم"],
}


def get_embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.OPENAI_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )


def detect_topics(text: str) -> list[str]:
    """Return which regulatory topics appear in the text."""
    lower = text.lower()
    return [
        topic
        for topic, keywords in TOPIC_KEYWORDS.items()
        if any(kw.lower() in lower for kw in keywords)
    ]


def _query_collection(collection_name: str, embedding: list[float], top_k: int) -> list[dict]:
    """Query a single ChromaDB collection and return scored chunks."""
    try:
        col = get_or_create_collection(collection_name)
        if col.count() == 0:
            return []
        results = col.query(
            query_embeddings=[embedding],
            n_results=min(top_k, col.count()),
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "text": doc,
                "metadata": meta,
                "score": 1.0 - dist,  
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]
    except Exception:
        return []


def hierarchical_retrieve(
    query: str,
    context_type: str = "general",
    top_k_per_tier: int | None = None,
) -> dict:
    """
    Priority-based retrieval across all indexed document collections.

    Algorithm:
      1. Query every collection independently (top_k each).
      2. Collect topics covered by Priority-1 & Priority-2 chunks.
      3. Suppress Priority-6 (Urban Planning 2021) chunks whose topics
         overlap with those high-priority topics.
      4. Return structured result with active/suppressed metadata.
    """
    top_k = top_k_per_tier or settings.TOP_K_PER_TIER
    embedder = get_embedder()
    query_embedding = embedder.embed_query(query)

    indexed = set(list_indexed_collections())
    sorted_registry = sorted(settings.DOCUMENT_REGISTRY, key=lambda d: d["priority"])

    all_chunks: list[dict] = []
    for doc_meta in sorted_registry:
        if doc_meta["collection"] not in indexed:
            continue
        chunks = _query_collection(doc_meta["collection"], query_embedding, top_k)
        for c in chunks:
            c["priority"] = doc_meta["priority"]
            c["can_be_suppressed"] = doc_meta.get("can_be_suppressed", False)
        all_chunks.extend(chunks)

    # Suppression Logic 
    high_priority_topics: set[str] = set()
    for chunk in all_chunks:
        if chunk["priority"] <= 2:
            high_priority_topics.update(detect_topics(chunk["text"]))

    active_chunks: list[dict] = []
    suppressed_laws: list[str] = []
    suppression_reasons: list[str] = []

    for chunk in all_chunks:
        if chunk.get("can_be_suppressed") and high_priority_topics:
            overlap = set(detect_topics(chunk["text"])) & high_priority_topics
            if overlap:
                law_en = chunk["metadata"].get("law_name_en", "Unknown")
                if law_en not in suppressed_laws:
                    suppressed_laws.append(law_en)
                    suppression_reasons.append(
                        f"'{law_en}' conflicts with higher priority laws on topics {sorted(overlap)}. "
                        f"Check if it applies based on context_type."
                    )
                
        active_chunks.append(chunk)


    active_chunks.sort(key=lambda c: c["score"] - (c["priority"] * 0.02), reverse=True)

    active_laws = list({c["metadata"].get("law_name_en", "") for c in active_chunks})

    return {
        "chunks": active_chunks,
        "active_laws": active_laws,
        "suppressed_laws": suppressed_laws,
        "suppression_reasons": suppression_reasons,
    }
