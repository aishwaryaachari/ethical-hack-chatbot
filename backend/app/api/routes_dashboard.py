from fastapi import APIRouter
from app.core import audit

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/events")
def events(limit: int = 100):
    return {"events": audit.recent(limit)}


@router.get("/dashboard/stats")
def stats():
    return audit.stats()


@router.get("/health")
def health():
    from app.db.mongo import get_db
    return {"ok": True, "mongo": get_db() is not None}


@router.get("/llm/status")
def llm_status():
    from app.agents import groq_agent
    return groq_agent.status()


from pydantic import BaseModel


class UserIn(BaseModel):
    user_id: str
    email: str
    role: str = "viewer"
    tenant_id: str = "tenant_acme"


@router.post("/users")
def add_user(body: UserIn):
    """Add a new user directly to MongoDB (or memory)."""
    user_data = body.dict()
    try:
        from app.db.mongo import get_db
        db = get_db()
        if db is not None:
            db.users.update_one({"user_id": body.user_id}, {"$set": user_data}, upsert=True)
            return {"ok": True, "user": user_data, "source": "mongodb"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    from app.db.synthetic_data import USERS
    USERS.append(user_data)
    return {"ok": True, "user": user_data, "source": "memory"}


@router.get("/users")
def get_users():
    """REAL registered users from MongoDB users collection (fallback: synthetic seed)."""
    try:
        from app.db.mongo import get_db
        db = get_db()
        if db is not None:
            u_list = list(db.users.find({}, {"_id": 0}))
            t_list = list(db.tenants.find({}, {"_id": 0}))
            if u_list:
                return {"users": u_list, "tenants": t_list, "source": "mongodb"}
    except Exception:
        pass
    from app.db.synthetic_data import USERS, TENANTS
    return {"users": USERS, "tenants": TENANTS, "source": "synthetic-fallback"}

