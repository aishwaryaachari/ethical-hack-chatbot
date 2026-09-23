"""Topics: per-user notebooks grouping uploaded PDFs. Mongo with memory fallback."""
import uuid
from datetime import datetime, timezone

_mem_topics: list = []
_mem_docs: list = []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db():
    try:
        from app.db.mongo import get_db
        return get_db()
    except Exception:
        return None


def reset_all() -> dict:
    """Factory reset for re-demo: clears topics + doc registry (memory + mongo)."""
    _mem_topics.clear()
    _mem_docs.clear()
    db = _db()
    if db is not None:
        try:
            db.topics.delete_many({})
            db.uploaded_documents.delete_many({})
        except Exception:
            pass
    return {"topics_cleared": True}


def create(owner_id: str, tenant_id: str, title: str) -> dict:
    t = {"topic_id": f"t_{uuid.uuid4().hex[:8]}", "owner_id": owner_id,
         "tenant_id": tenant_id, "title": (title or "").strip()[:80] or "Untitled topic",
         "created_at": _now(), "doc_count": 0}
    db = _db()
    if db is not None:
        try:
            db.topics.insert_one(dict(t))
            return t
        except Exception:
            pass
    _mem_topics.append(t)
    return t


def list_for_owner(owner_id: str) -> list:
    db = _db()
    if db is not None:
        try:
            return list(db.topics.find({"owner_id": owner_id}, {"_id": 0}).sort("created_at", -1))
        except Exception:
            pass
    return sorted([t for t in _mem_topics if t["owner_id"] == owner_id],
                  key=lambda t: t["created_at"], reverse=True)


def get(topic_id: str) -> dict | None:
    db = _db()
    if db is not None:
        try:
            return db.topics.find_one({"topic_id": topic_id}, {"_id": 0})
        except Exception:
            pass
    return next((t for t in _mem_topics if t["topic_id"] == topic_id), None)


def register_doc(record: dict) -> None:
    """Record an uploaded doc (with topic_id) for the topic-detail file list."""
    record = dict(record)
    db = _db()
    if db is not None:
        try:
            db.uploaded_documents.insert_one(record)
            db.topics.update_one({"topic_id": record.get("topic_id")}, {"$inc": {"doc_count": 1}})
            return
        except Exception:
            pass
    _mem_docs.append(record)
    for t in _mem_topics:
        if t["topic_id"] == record.get("topic_id"):
            t["doc_count"] = t.get("doc_count", 0) + 1


def docs_for_topic(topic_id: str, owner_id: str) -> list:
    db = _db()
    if db is not None:
        try:
            return list(db.uploaded_documents.find(
                {"topic_id": topic_id, "owner_id": owner_id}, {"_id": 0}))
        except Exception:
            pass
    return [d for d in _mem_docs if d.get("topic_id") == topic_id and d.get("owner_id") == owner_id]


def delete(topic_id: str, owner_id: str) -> dict:
    """Delete topic + its doc records. Returns doc_ids so chunks can be purged."""
    docs = docs_for_topic(topic_id, owner_id)
    db = _db()
    if db is not None:
        try:
            db.topics.delete_one({"topic_id": topic_id, "owner_id": owner_id})
            db.uploaded_documents.delete_many({"topic_id": topic_id, "owner_id": owner_id})
        except Exception:
            pass
    else:
        _mem_topics[:] = [t for t in _mem_topics
                          if not (t["topic_id"] == topic_id and t["owner_id"] == owner_id)]
        _mem_docs[:] = [d for d in _mem_docs
                        if not (d.get("topic_id") == topic_id and d.get("owner_id") == owner_id)]
    try:
        from app.rag import store
        store.delete_by_topic(topic_id)
    except Exception:
        pass
    return {"deleted": True, "topic_id": topic_id, "docs_removed": len(docs)}


def delete_doc(doc_id: str, owner_id: str) -> dict:
    """Delete ONE document: registry record + all its chunks. Verifies owner."""
    db = _db()
    rec = None
    if db is not None:
        try:
            rec = db.uploaded_documents.find_one(
                {"doc_id": doc_id, "owner_id": owner_id}, {"_id": 0})
            if rec:
                db.uploaded_documents.delete_one(
                    {"doc_id": doc_id, "owner_id": owner_id})
                db.topics.update_one(
                    {"topic_id": rec.get("topic_id"), "owner_id": owner_id},
                    {"$inc": {"doc_count": -1}})
        except Exception:
            pass
    else:
        rec = next((d for d in _mem_docs
                    if d.get("doc_id") == doc_id and d.get("owner_id") == owner_id), None)
        if rec:
            _mem_docs.remove(rec)
            for t in _mem_topics:
                if t["topic_id"] == rec.get("topic_id") and t["owner_id"] == owner_id:
                    t["doc_count"] = max(0, t.get("doc_count", 1) - 1)
    if not rec:
        return {"deleted": False, "reason": "not found"}
    chunks = 0
    try:
        from app.rag import store
        chunks = store.delete_by_doc(doc_id)
    except Exception:
        pass
    return {"deleted": True, "doc_id": doc_id, "chunks_removed": chunks}
