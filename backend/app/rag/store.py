"""Vector store: ChromaDB local with in-memory fallback (no server needed)."""
from app.rag import embeddings as emb

_coll = None
_mem: list = []  # fallback: [{id, text, vector, metadata}]


def _chroma():
    global _coll
    if _coll is not None:
        return _coll
    try:
        import chromadb
        from app.core.config import settings
        client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
        _coll = client.get_or_create_collection("lab_kb")
        return _coll
    except Exception:
        return None


def _clean(meta: dict) -> dict:
    """Chroma rejects None metadata values — strip them (memory keeps full record)."""
    return {k: v for k, v in meta.items() if v is not None}


def add(doc_id: str, chunks: list, metadatas: list):
    vecs = [emb.embed(c) for c in chunks]
    emb.train(chunks + [m.get("seed_hint", "") for m in metadatas])
    global _mem
    _mem = [m for m in _mem if m["metadata"].get("doc_id") != doc_id]
    for i, (ch, md) in enumerate(zip(chunks, metadatas)):
        _mem.append({"id": f"{doc_id}#{i}", "text": ch, "vector": vecs[i], "metadata": md})

    c = _chroma()
    if c is not None:
        try:
            ids = [f"{doc_id}#{i}" for i in range(len(chunks))]
            batch_size = 50
            for start in range(0, len(chunks), batch_size):
                b_ids = ids[start:start + batch_size]
                b_chunks = chunks[start:start + batch_size]
                b_vecs = vecs[start:start + batch_size]
                b_metas = [_clean(m) for m in metadatas[start:start + batch_size]]
                try:
                    c.upsert(ids=b_ids, documents=b_chunks, embeddings=b_vecs, metadatas=b_metas)
                except Exception:
                    try:
                        c.delete(ids=b_ids)
                    except Exception:
                        pass
                    c.add(ids=b_ids, documents=b_chunks, embeddings=b_vecs, metadatas=b_metas)
            return {"backend": "chroma", "chunks": len(chunks)}
        except Exception:
            pass
    return {"backend": "memory", "chunks": len(chunks)}


def query(qtext: str, top_k: int = 3, tenant_filter: str | None = None,
            topic_filter: str | None = None) -> list:
    qv = emb.embed(qtext, is_query=True)
    c = _chroma()
    if c is not None:
        try:
            clauses = []
            if tenant_filter:
                clauses.append({"tenant_id": tenant_filter})
            if topic_filter:
                clauses.append({"topic_id": topic_filter})
            kwargs: dict = {"query_embeddings": [qv], "n_results": top_k}
            if len(clauses) == 1:
                kwargs["where"] = clauses[0]
            elif clauses:
                kwargs["where"] = {"$and": clauses}
            res = c.query(**kwargs)
            out = []
            for i in range(len(res["ids"][0])):
                out.append({"id": res["ids"][0][i], "text": res["documents"][0][i],
                            "score": round(float(res["distances"][0][i]), 4),
                            "metadata": res["metadatas"][0][i]})
            return out
        except Exception:
            pass
    scored = []
    for m in _mem:
        if tenant_filter and m["metadata"].get("tenant_id") != tenant_filter:
            continue
        if topic_filter and m["metadata"].get("topic_id") != topic_filter:
            continue
        scored.append((emb.cosine(qv, m["vector"]), m))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"id": m["id"], "text": m["text"], "score": round(float(s), 4),
             "metadata": m["metadata"]} for s, m in scored[:top_k]]


def delete_by_topic(topic_id: str) -> int:
    removed = 0
    global _mem
    kept = [m for m in _mem if m["metadata"].get("topic_id") != topic_id]
    removed += len(_mem) - len(kept)
    _mem = kept
    for k in list(_hidden.keys()):
        if topic_id in k:
            _hidden.pop(k, None)
    c = _chroma()
    if c is not None:
        try:
            ids = [i for i in c.get(where={"topic_id": topic_id})["ids"]]
            if ids:
                c.delete(ids=ids)
                removed += len(ids)
        except Exception:
            pass
    return removed


def delete_by_doc(doc_id: str) -> int:
    removed = 0
    global _mem
    kept = [m for m in _mem if m["metadata"].get("doc_id") != doc_id]
    removed += len(_mem) - len(kept)
    _mem = kept
    _hidden.pop(doc_id, None)
    c = _chroma()
    if c is not None:
        try:
            ids = [i for i in c.get(where={"doc_id": doc_id})["ids"]]
            if ids:
                c.delete(ids=ids)
                removed += len(ids)
        except Exception:
            pass
    return removed


def reset():
    _mem.clear()
    _hidden.clear()
    c = _chroma()
    if c is not None:
        try:
            for i in c.get()["ids"]:
                c.delete(ids=[i])
        except Exception:
            pass


# Hidden-layer payloads, keyed by doc_id. Kept OUT of the vector store so they
# can never be retrieved as context — the backend pastes them itself.
# Memory-only by design (reset() wipes them); the demo flow is upload → query.
_hidden: dict = {}


def set_hidden(doc_id: str, hidden_text: str) -> None:
    if hidden_text and hidden_text.strip():
        _hidden[doc_id] = hidden_text[:2000]


def get_hidden(doc_id: str | None) -> str:
    return _hidden.get(doc_id or "", "")


def get_all_hidden() -> dict:
    return dict(_hidden)


def peek(limit: int = 20) -> list:
    """LAB-ONLY debug view: current raw chunk texts in the store."""
    c = _chroma()
    if c is not None:
        try:
            res = c.get(limit=limit)
            return [{"id": i, "text": d[:200], "metadata": m}
                    for i, d, m in zip(res["ids"], res["documents"], res["metadatas"])]
        except Exception:
            pass
    return [{"id": m["id"], "text": m["text"][:200], "metadata": m["metadata"]}
            for m in _mem[:limit]]


def doc_texts(doc_id: str) -> list:
    """Full chunk texts for one uploaded doc (used to weaponize a PDF)."""
    c = _chroma()
    if c is not None:
        try:
            res = c.get(where={"doc_id": doc_id})
            if res["ids"]:
                return list(res["documents"])
        except Exception:
            pass
    return [m["text"] for m in _mem if m["metadata"].get("doc_id") == doc_id]


def rewrite_all(new_text: str) -> dict:
    """LAB-ONLY tamper primitive: overwrite EVERY chunk's text AND vector.

    Re-embedding keeps the poison retrievable (a real tamperer would do the
    same). No LLM is touched anywhere in this path.
    """
    vec = emb.embed(new_text)
    emb.train([new_text])
    n_mem = 0
    for m in _mem:
        m["text"] = new_text
        m["vector"] = list(vec)
        n_mem += 1
    n_chroma = 0
    c = _chroma()
    if c is not None:
        try:
            ids = list(c.get()["ids"])
            if ids:
                c.update(ids=ids,
                         embeddings=[list(vec)] * len(ids),
                         documents=[new_text] * len(ids))
                n_chroma = len(ids)
        except Exception:
            pass
    return {"memory_rewritten": n_mem, "chroma_rewritten": n_chroma}
