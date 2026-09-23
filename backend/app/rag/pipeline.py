"""ATTACK 2: RAG poisoning / cross-user context injection + store tampering."""
from datetime import datetime, timezone
from app.pdf import parser as pdf
from app.rag import store
from app.security import detector as det
from app.agents import groq_agent
from app.core import audit


def _is_poison_hit(h: dict) -> bool:
    """A chunk counts as attacker-controlled if it was quarantined at upload,
    scored high, or still matches an injection pattern."""
    md = h.get("metadata", {}) or {}
    if md.get("quarantined"):
        return True
    if md.get("poison_score", 0) >= 0.4:
        return True
    try:
        return bool(det.detect(h.get("text", ""))["is_injection"])
    except Exception:
        return False


def _same_scope(h: dict, victim_tenant: str, topic_id: str | None) -> bool:
    """True if the chunk belongs to the victim's own tenant/topic."""
    md = h.get("metadata", {}) or {}
    if md.get("tenant_id") != victim_tenant:
        return False
    if topic_id and md.get("topic_id") != topic_id:
        return False
    return True


def poison_shared(owner_id: str, tenant_id: str, text: str | None = None,
                  source_doc_id: str | None = None, mode: str = "vulnerable") -> dict:
    """LAB-ONLY RAG content tampering. Rewrites the shared KB for EVERYONE.

    No LLM is invoked anywhere in this path — the attack lands directly on
    the store (Chroma + memory fallback). In vulnerable mode the write goes
    through with no ownership check; in protected mode the shared KB is
    treated as immutable and the write is denied + logged.
    """
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if source_doc_id:
        doc_text = "\n".join(store.doc_texts(source_doc_id))
        if doc_text:
            text = doc_text
    text = (text or "")[:2000]
    d = det.detect(text)
    before = store.peek(3)

    if mode == "vulnerable":
        payload = f"[POISONED BY {owner_id}] {text}"
        res = store.rewrite_all(payload)
        audit.log("rag-tamper", "CRITICAL",
                  f"SIMULATED SUCCESS — shared RAG content rewritten by {owner_id}",
                  {"rewritten": res, "detection": d})
        return {"mode": mode, "attack": "RAG Store Tampering (global content rewrite)",
                "result": "SIMULATED SUCCESS",
                "rewritten": res, "before": before, "after": store.peek(3),
                "detection": d, "timestamp": ts,
                "impact": "Every user/topic now retrieves attacker-controlled text."}

    audit.log("rag-tamper", "HIGH" if d["is_injection"] else "MEDIUM",
              f"BLOCKED — content rewrite denied for {owner_id}",
              {"reason": "shared KB immutable without owner-signed write",
               "detection": d})
    return {"mode": mode, "attack": "RAG Store Tampering (global content rewrite)",
            "result": "BLOCKED",
            "reason": "shared KB immutable without owner-signed write",
            "detection": d, "store_unchanged": True, "sample": before,
            "timestamp": ts}


def upload_pdf(data: bytes, filename: str, owner_id: str, tenant_id: str,
               topic_id: str | None = None) -> dict:
    layers = pdf.extract_layers(data)
    text, hidden = layers["visible"], layers["hidden"]
    # Only treat micro-text as a hidden payload if it actually contains
    # an injection pattern, brand plug, or override directive.
    # Normal PDF footnotes, subscripts, and page numbers (e.g. 10, 2, 1, 0, commas) are layout noise.
    if hidden:
        d_hidden = det.detect(hidden)
        has_payload = bool(d_hidden["is_injection"] or "pillai.com" in hidden or "anonymous" in hidden or "override" in hidden.lower())
        if not has_payload:
            text = (text + "\n" + hidden).strip()
            hidden = ""
    # Detection runs over BOTH layers — the payload usually hides below.
    d = det.detect((text + "\n" + hidden)[:20000])
    scripting = pdf.detect_scripting(data)
    scope = topic_id or "shared"
    doc_id = f"{tenant_id}_{owner_id}_{scope}_{filename}".replace(" ", "_")
    metas = [{"doc_id": doc_id, "owner_id": owner_id, "tenant_id": tenant_id,
              "topic_id": topic_id,
              "chunk_id": i, "poison_score": d["score"],
              "quarantined": bool(d["is_injection"] or scripting["scripting_detected"])}
             for i in range(len(pdf.chunk(text)))]
    res = store.add(doc_id, pdf.chunk(text), metas)
    store.set_hidden(doc_id, hidden)
    severity = "CRITICAL" if scripting["scripting_detected"] else ("HIGH" if d["is_injection"] else "INFO")
    audit.log("attack2-upload", severity,
              f"PDF uploaded by {owner_id}: {filename} poison={d['is_injection']} scripting={scripting['scripting_detected']}",
              {"doc_id": doc_id, "detection": d, "scripting": scripting})
    from app.rag import topics as _topics
    _topics.register_doc(
        {"doc_id": doc_id, "owner_id": owner_id, "tenant_id": tenant_id,
         "topic_id": topic_id, "filename": filename, "poison": d["is_injection"],
         "chunks": res["chunks"]})
    return {"doc_id": doc_id, "chunks": res["chunks"], "detection": d,
            "scripting": scripting, "topic_id": topic_id,
            "visible_chars": len(text), "hidden_chars": len(hidden),
            "warning": "Stored as UNTRUSTED DATA. Poison scan applied."}


def ask(question: str, victim_id: str, victim_tenant: str, mode: str,
        topic_id: str | None = None) -> dict:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if mode == "vulnerable":
        # VULN DEMO (fixed isolation): clean docs are strictly isolated to the
        # victim's own tenant/topic — a benign system-design.pdf in topic A
        # NEVER leaks into topic B. ONLY attacker-controlled (quarantined /
        # injection) chunks such as hack.pdf leak cross-tenant/topic, which is
        # exactly the poisoning attack being demonstrated.
        own_hits = store.query(question, top_k=4,
                               tenant_filter=victim_tenant, topic_filter=topic_id)
        candidates = store.query(question, top_k=10,
                                 tenant_filter=None, topic_filter=None)
        leaked = [h for h in candidates
                  if not _same_scope(h, victim_tenant, topic_id) and _is_poison_hit(h)]
        # Merge: leaked poison first (attack), then own docs. De-dup by id.
        seen, hits = set(), []
        for h in leaked + own_hits:
            if h["id"] not in seen:
                seen.add(h["id"])
                hits.append(h)
        hits = hits[:4]
        context = "\n\n".join([f"<DOCUMENT id={h['id']}>\n{h['text'][:2500]}\n</DOCUMENT>" for h in hits])
        llm = groq_agent.generate(question, context=context, persona="vulnerable")
        # Hidden layer: only paste hidden payloads that are either the
        # victim's own docs or attacker poison (hack.pdf). Clean docs from
        # OTHER tenants/topics are never pasted.
        hidden_blocks = []
        for doc_id, hp in store.get_all_hidden().items():
            if not hp or hp in hidden_blocks:
                continue
            try:
                is_poison_hidden = bool(det.detect(hp)["is_injection"])
            except Exception:
                is_poison_hidden = False
            belongs_to_victim = doc_id.startswith(f"{victim_tenant}_") or (
                topic_id and topic_id in doc_id)
            if is_poison_hidden or belongs_to_victim:
                hidden_blocks.append(hp)
        if hidden_blocks:
            llm["answer"] = (llm.get("answer") or "") + (
                "\n\n--- Retrieved context ---\n" + "\n\n".join(hidden_blocks))
        poisoned = bool(hidden_blocks) or any(_is_poison_hit(h) for h in hits)
        cross = any(not _same_scope(h, victim_tenant, topic_id) for h in hits)
        if not hits and not hidden_blocks:
            # Nothing in the victim's own docs (and no poison) covers this —
            # answer from UPLOADED CONTENT ONLY: admit no knowledge, never go
            # outside to general knowledge or other users' data.
            llm = {"answer": groq_agent.NO_KNOWLEDGE_ANSWER,
                   "provider": "grounding-guard:no-knowledge"}
        chain = [{"node": "VICTIM_QUERY", "label": question[:60]},
                 {"node": "RETRIEVER", "label": "own tenant/topic isolated; poison leaks (vuln)"},
                 {"node": "CHUNKS", "label": f"{len(hits)} chunks ({len(leaked)} leaked poison + own docs)" if hits else "no hits"},
                 {"node": "LLM", "label": "trusted poisoned context → influenced answer"}]
        audit.log("attack2", "CRITICAL" if poisoned else "MEDIUM",
                  "SIMULATED SUCCESS — RAG poisoning influenced victim answer" if poisoned
                  else "RAG query (vuln mode, no poison hit)",
                  {"victim": victim_id, "hits": [h["id"] for h in hits]})
        result = ("SIMULATED SUCCESS" if poisoned
                  else ("NO KNOWLEDGE" if (not hits and not hidden_blocks)
                        else "NO POISON RETRIEVED"))
        if "don't have knowledge" in (llm.get("answer") or ""):
            result = "NO KNOWLEDGE"
        return {"mode": mode, "attack": "RAG Poisoning / Cross-User Injection",
                "result": result,
                "poisoned": poisoned, "cross_tenant_leak": cross,
                "retrieved_chunks": [{"id": h["id"], "owner": h["metadata"].get("owner_id"),
                                      "tenant": h["metadata"].get("tenant_id"),
                                      "score": h["score"], "text": h["text"][:400],
                                      "why": ("LEAKED poison from another tenant/topic (vuln)"
                                              if not _same_scope(h, victim_tenant, topic_id)
                                              else "own tenant/topic doc")}
                                     for h in hits],
                "llm": llm, "chain": chain, "timestamp": ts,
                "impact": ("Victim answer influenced by attacker's doc." if poisoned
                           else "No poisoned chunk in top-k this query.")}
    # Protected: tenant isolation + untrusted tagging + strip
    hits = store.query(question, top_k=4, tenant_filter=victim_tenant, topic_filter=topic_id)
    safe, blocked = [], []
    for h in hits:
        d = det.detect(h["text"])
        if d["is_injection"] or h["metadata"].get("quarantined"):
            blocked.append({"id": h["id"], "score": h["score"], "reason": "poison detected, excluded"})
        else:
            safe.append(h)
    context = "\n\n".join([f"<DOCUMENT id={h['id']}>\n{h['text'][:2500]}\n</DOCUMENT>" for h in safe])
    if not safe:
        # Nothing in the victim's own docs covers this — never fall back to
        # outside knowledge or other users' data.
        llm = {"answer": groq_agent.NO_KNOWLEDGE_ANSWER,
               "provider": "grounding-guard:no-knowledge"}
    else:
        llm = groq_agent.generate(question, context=context or "(no trusted context)",
                                    persona="protected")
    chain = [{"node": "VICTIM_QUERY", "label": question[:60]},
             {"node": "RETRIEVER", "label": f"tenant filter = {victim_tenant}"},
             {"node": "VALIDATOR", "label": f"{len(safe)} safe / {len(blocked)} blocked as untrusted"},
             {"node": "LLM", "label": "hardened system prompt, poison ignored"}]
    audit.log("attack2", "HIGH" if blocked else "INFO",
              f"BLOCKED — {len(blocked)} poisoned/cross-tenant chunks excluded" if blocked
              else "RAG query isolated, no poison",
              {"victim": victim_id, "blocked": blocked})
    return {"mode": "protected", "attack": "RAG Poisoning / Cross-User Injection",
            "result": "BLOCKED" if blocked else ("NO KNOWLEDGE" if not safe else "ISOLATED"),
            "retrieved_chunks": [{"id": h["id"], "owner": h["metadata"].get("owner_id"),
                                  "tenant": h["metadata"].get("tenant_id"), "score": h["score"],
                                  "text": h["text"][:400], "why": "own-tenant only, tagged UNTRUSTED"}
                                 for h in safe],
            "blocked_chunks": blocked, "llm": llm, "chain": chain, "timestamp": ts}
