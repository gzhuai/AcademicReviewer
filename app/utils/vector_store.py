import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_chroma_client = None
_collection = None

COLLECTION_NAME = "academic_documents"


def _get_chroma():
    global _chroma_client, _collection
    if _chroma_client is None:
        import chromadb
        path = Path(settings.chroma_persist_dir)
        path.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(path))
        try:
            _collection = _chroma_client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            _collection = _chroma_client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        logger.info(f"ChromaDB initialized at {path}, docs={_collection.count()}")
    return _chroma_client, _collection


def index_document(
    text: str,
    doc_id: str,
    metadata: dict | None = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> int:
    _, collection = _get_chroma()

    words = text.split()
    chunks = []
    chunk_metas = []
    chunk_ids = []

    start = 0
    idx = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append(chunk_text)
        chunk_metas.append({
            **(metadata or {}),
            "chunk_index": idx,
            "total_chunks": 0,
        })
        chunk_ids.append(f"{doc_id}_chunk_{idx}")
        start = end - chunk_overlap if end < len(words) else end
        idx += 1

    total = len(chunks)
    for m in chunk_metas:
        m["total_chunks"] = total

    if chunks:
        collection.add(
            documents=chunks,
            metadatas=chunk_metas,
            ids=chunk_ids,
        )

    logger.info(f"Indexed doc {doc_id}: {total} chunks")
    return total


def query_similar(
    text: str,
    top_k: int = 5,
    min_distance: float = 0.0,
) -> list[dict]:
    _, collection = _get_chroma()

    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[text[:8000]],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results["distances"] else 0
            similarity = 1 - distance if distance <= 1 else max(0, 1 - distance)
            if similarity < min_distance:
                continue
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            hits.append({
                "id": doc_id,
                "similarity": round(similarity, 4),
                "metadata": meta,
                "text_snippet": (results["documents"][0][i][:200] + "...") if results["documents"] else "",
            })

    return hits


def check_originality(
    text: str,
    top_k: int = 10,
    high_similarity_threshold: float = 0.75,
    medium_similarity_threshold: float = 0.50,
) -> dict:
    hits = query_similar(text, top_k=top_k)

    high_count = sum(1 for h in hits if h["similarity"] >= high_similarity_threshold)
    medium_count = sum(1 for h in hits if medium_similarity_threshold <= h["similarity"] < high_similarity_threshold)
    max_sim = max((h["similarity"] for h in hits), default=0.0)
    avg_sim = sum(h["similarity"] for h in hits) / len(hits) if hits else 0.0

    if high_count > 0:
        originality_score = max(1, 10 - high_count * 3 - medium_count * 1.5)
    elif medium_count > 2:
        originality_score = max(3, 10 - medium_count * 1.5)
    elif avg_sim > 0.3:
        originality_score = 7
    else:
        originality_score = 9

    similarity_flags = []
    for h in hits:
        if h["similarity"] >= high_similarity_threshold:
            similarity_flags.append({
                "level": "high",
                "source": h["id"],
                "similarity": h["similarity"],
                "snippet": h["text_snippet"],
            })
        elif h["similarity"] >= medium_similarity_threshold:
            similarity_flags.append({
                "level": "medium",
                "source": h["id"],
                "similarity": h["similarity"],
                "snippet": h["text_snippet"],
            })

    return {
        "originality_score": originality_score,
        "total_docs_compared": collection_count(),
        "top_k_checked": top_k,
        "max_similarity": round(max_sim, 4),
        "avg_similarity": round(avg_sim, 4),
        "high_similarity_count": high_count,
        "medium_similarity_count": medium_count,
        "similarity_flags": similarity_flags,
    }


def remove_document(doc_id: str) -> bool:
    _, collection = _get_chroma()
    try:
        existing = collection.get(ids=[f"{doc_id}_chunk_0"])
        if existing and existing["ids"]:
            chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(100)]
            actual_ids = [cid for cid in chunk_ids if cid in collection.get(ids=chunk_ids).get("ids", [])]
            if actual_ids:
                collection.delete(ids=actual_ids)
                logger.info(f"Removed {len(actual_ids)} chunks for doc {doc_id}")
                return True
        return False
    except Exception as e:
        logger.warning(f"Failed to remove doc {doc_id}: {e}")
        return False


def collection_count() -> int:
    try:
        _, collection = _get_chroma()
        return collection.count()
    except Exception:
        return 0
