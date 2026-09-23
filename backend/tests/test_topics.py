"""Topics: per-user isolation — docs in topic A never leak into topic B."""
from app.rag import pipeline, topics, store


def _reset():
    store.reset()
    topics._mem_topics.clear()
    topics._mem_docs.clear()
    try:
        from app.db.mongo import get_db
        db = get_db()
        if db is not None:
            db.topics.delete_many({})
            db.uploaded_documents.delete_many({})
    except Exception:
        pass


def test_topic_scoped_upload_and_query():
    _reset()
    a = topics.create("u_tanush", "tenant_acme", "Invoices")
    b = topics.create("u_tanush", "tenant_acme", "HR")
    pipeline.upload_pdf(b"Acme invoice totals: 42 demo credits. Synthetic only.",
                        "inv.pdf", "u_tanush", "tenant_acme", a["topic_id"])
    r_in = pipeline.ask("invoice totals?", "u_tanush", "tenant_acme", "protected", a["topic_id"])
    assert any("invoice" in c["text"].lower() for c in r_in["retrieved_chunks"])
    r_out = pipeline.ask("invoice totals?", "u_tanush", "tenant_acme", "protected", b["topic_id"])
    assert all("invoice totals" not in c["text"].lower() for c in r_out["retrieved_chunks"])


def test_topic_crud_and_docs():
    _reset()
    t = topics.create("u_tanush", "tenant_acme", "Research")
    assert topics.list_for_owner("u_tanush")[0]["topic_id"] == t["topic_id"]
    pipeline.upload_pdf(b"Synthetic research note.", "note.pdf",
                        "u_tanush", "tenant_acme", t["topic_id"])
    docs = topics.docs_for_topic(t["topic_id"], "u_tanush")
    assert len(docs) == 1 and docs[0]["filename"] == "note.pdf"
    assert topics.list_for_owner("u_tanush")[0]["doc_count"] == 1
    out = topics.delete(t["topic_id"], "u_tanush")
    assert out["deleted"] is True
    assert topics.list_for_owner("u_tanush") == []
    # chunks purged too
    assert store.query("research note", topic_filter=t["topic_id"]) == []
