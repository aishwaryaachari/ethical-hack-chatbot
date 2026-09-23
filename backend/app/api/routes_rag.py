from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from app.rag import pipeline
from app.rag import topics as topic_store

router = APIRouter(prefix="/api/rag", tags=["rag"])


class TopicIn(BaseModel):
    owner_id: str
    tenant_id: str
    title: str


@router.post("/topics")
def create_topic(body: TopicIn):
    return topic_store.create(body.owner_id, body.tenant_id, body.title)


@router.get("/topics")
def list_topics(owner_id: str):
    return {"topics": topic_store.list_for_owner(owner_id)}


@router.get("/topics/{topic_id}/docs")
def topic_docs(topic_id: str, owner_id: str):
    t = topic_store.get(topic_id)
    if not t or t["owner_id"] != owner_id:
        return {"docs": []}
    return {"topic": t, "docs": topic_store.docs_for_topic(topic_id, owner_id)}


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: str, owner_id: str):
    t = topic_store.get(topic_id)
    if not t or t["owner_id"] != owner_id:
        return {"deleted": False, "reason": "not found"}
    return topic_store.delete(topic_id, owner_id)


@router.delete("/docs/{doc_id}")
def delete_doc(doc_id: str, owner_id: str):
    return topic_store.delete_doc(doc_id, owner_id)


@router.post("/upload")
async def upload(file: UploadFile = File(...), owner_id: str = Form("u_anon"),
                 tenant_id: str = Form("tenant_acme"), topic_id: str | None = Form(None)):
    data = await file.read()
    topic_id = topic_id or None
    if topic_id:
        t = topic_store.get(topic_id)
        if not t or t["owner_id"] != owner_id:
            return {"error": "unknown topic for this user"}
    return pipeline.upload_pdf(data, file.filename or "doc.pdf", owner_id, tenant_id, topic_id)


class AskIn(BaseModel):
    question: str
    victim_id: str = "u_aishwarya"
    victim_tenant: str = "tenant_globex"
    mode: str = "vulnerable"
    topic_id: str | None = None


@router.post("/query")
def query(body: AskIn):
    assert body.mode in ("vulnerable", "protected")
    return pipeline.ask(body.question, body.victim_id, body.victim_tenant, body.mode, body.topic_id)


class PoisonIn(BaseModel):
    owner_id: str = "u_anon"
    tenant_id: str = "tenant_acme"
    text: str | None = None
    source_doc_id: str | None = None
    mode: str = "vulnerable"


@router.post("/poison")
def poison(body: PoisonIn):
    assert body.mode in ("vulnerable", "protected")
    return pipeline.poison_shared(body.owner_id, body.tenant_id,
                                  body.text, body.source_doc_id, body.mode)


@router.get("/dump")
def dump(limit: int = 10):
    from app.rag import store
    return {"chunks": store.peek(limit)}


@router.post("/reset")
def reset():
    from app.rag import store
    store.reset()
    topic_store.reset_all()
    return {"ok": True}
