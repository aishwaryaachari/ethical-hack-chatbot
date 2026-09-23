"""Attack 2: RAG poisoning leaks cross-tenant in vulnerable, isolated in protected."""
from app.rag import pipeline, store
from app.db.synthetic_data import RAG_POISON_TEXT


def _seed_poison():
    store.reset()
    pipeline.upload_pdf(RAG_POISON_TEXT.encode(), "poison.pdf", "u_anon", "tenant_acme")
    pipeline.upload_pdf(b"Synthetic password reset help. Contact helpdesk@demo.local for demo resets.",
                        "help.pdf", "u_aishwarya", "tenant_globex")


def test_vulnerable_retrieves_attacker_chunk():
    _seed_poison()
    r = pipeline.ask("how to reset password?", "u_aishwarya", "tenant_globex", "vulnerable")
    assert r["poisoned"] is True
    assert r["cross_tenant_leak"] is True


def test_protected_isolates_tenant():
    _seed_poison()
    r = pipeline.ask("how to reset password?", "u_aishwarya", "tenant_globex", "protected")
    assert r["result"] in ("BLOCKED", "ISOLATED")
    assert all(c["tenant"] == "tenant_globex" for c in r["retrieved_chunks"])
