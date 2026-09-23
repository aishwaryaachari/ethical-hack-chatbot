"""Single-doc delete: removes registry record + chunks, keeps sibling docs."""
from app.rag import pipeline, store
from app.rag import topics as topic_store


def test_delete_one_doc_keeps_sibling():
    store.reset()
    t = topic_store.create("u_tanush", "tenant_acme", "DelTest")
    pipeline.upload_pdf(b"Alpha invoice content here.", "a.pdf",
                        "u_tanush", "tenant_acme", t["topic_id"])
    pipeline.upload_pdf(b"Beta invoice content here.", "b.pdf",
                        "u_tanush", "tenant_acme", t["topic_id"])
    docs = topic_store.docs_for_topic(t["topic_id"], "u_tanush")
    assert len(docs) == 2
    victim = next(d for d in docs if d["filename"] == "a.pdf")
    r = topic_store.delete_doc(victim["doc_id"], "u_tanush")
    assert r["deleted"] is True
    assert r["chunks_removed"] >= 1
    rest = topic_store.docs_for_topic(t["topic_id"], "u_tanush")
    assert [d["filename"] for d in rest] == ["b.pdf"]
    assert all("Alpha invoice" not in c["text"] for c in store.peek(20))
    assert any("Beta invoice" in c["text"] for c in store.peek(20))


def test_delete_doc_wrong_owner_refused():
    store.reset()
    t = topic_store.create("u_tanush", "tenant_acme", "DelTest2")
    pipeline.upload_pdf(b"Private content here.", "p.pdf",
                        "u_tanush", "tenant_acme", t["topic_id"])
    doc_id = topic_store.docs_for_topic(t["topic_id"], "u_tanush")[0]["doc_id"]
    r = topic_store.delete_doc(doc_id, "u_aishwarya")
    assert r["deleted"] is False
    assert len(topic_store.docs_for_topic(t["topic_id"], "u_tanush")) == 1
