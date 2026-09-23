"""SAFE SIMULATED sandbox tools. No os.environ, no subprocess, no file/URL access."""
from app.db.synthetic_data import (
    USERS, SYNTHETIC_ENV, SYNTHETIC_CONFIG, SYNTHETIC_DB_RECORDS, SYNTHETIC_SECRETS,
)


def get_user(email: str, tenant_id: str):
    for u in USERS:
        if u["email"] == email and u["tenant_id"] == tenant_id:
            return {"email": u["email"], "role": u["role"], "tenant_id": u["tenant_id"]}
    return {"error": "user not found in tenant"}


def search_users(query: str, tenant_id: str):
    return [u for u in USERS if u["tenant_id"] == tenant_id
            and query.lower() in u["email"].lower()][:5]


def _read_dotenv_file(path: str) -> dict:
    """Parse a KEY=VALUE dotenv file into a dict. Empty dict if unreadable."""
    import os
    parsed = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        parsed[k.strip()] = v.strip()
        except Exception:
            pass
    return parsed


def get_environment():
    """Returns the REAL local environment configuration (backend/.env).

    Vulnerable mode deliberately exposes this — that IS the demonstrated leak.
    """
    import os
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    real = _read_dotenv_file(os.path.join(here, ".env"))
    if real:
        return real
    env_example_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env.example")
    simulated = _read_dotenv_file(env_example_path)
    if simulated:
        return simulated
    return dict(SYNTHETIC_ENV)


def get_database_schema():
    try:
        from app.db.mongo import get_db
        db = get_db()
        if db is not None:
            return {"database": "demo_lab", "collections": db.list_collection_names(), "note": "MongoDB lab database"}
    except Exception:
        pass
    return {"database": "demo_lab", "collections": ["users", "audit_events"], "note": "MongoDB lab database"}


def query_demo_database(tenant_id: str | None = None, *args, **kwargs):
    """Queries MongoDB users collection for the requested tenant."""
    try:
        from app.db.mongo import get_db
        db = get_db()
        if db is not None:
            q = {"tenant_id": tenant_id} if tenant_id else {}
            users = list(db.users.find(q, {"_id": 0}))
            if users:
                return users
    except Exception:
        pass
    if tenant_id:
        return [u for u in USERS if u["tenant_id"] == tenant_id]
    return list(USERS)


def get_application_config():
    """Returns the REAL local application config (backend/.env)."""
    import os
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    real = _read_dotenv_file(os.path.join(here, ".env"))
    if real:
        return {
            "app_name": "AI Ethical Hacker Lab",
            "environment": real.get("ENVIRONMENT", "development"),
            "api_port": real.get("API_PORT", "8000"),
            "database_uri": real.get("MONGO_URI", ""),
            "groq_model": real.get("GROQ_MODEL", ""),
            "groq_api_key": real.get("GROQ_API_KEY", ""),
            "chroma_dir": real.get("CHROMA_DIR", ""),
            "auth_mode": "multi-tenant-rbac",
        }
    env_example_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env.example")
    simulated = _read_dotenv_file(env_example_path)
    if simulated:
        return simulated
    return dict(SYNTHETIC_CONFIG)


def get_admin_resource(tenant_id: str | None = None, *args, **kwargs):
    """Returns admin resources (MongoDB registered users) for tenant."""
    try:
        from app.db.mongo import get_db
        db = get_db()
        if db is not None:
            q = {"tenant_id": tenant_id} if tenant_id else {}
            users = list(db.users.find(q, {"_id": 0}))
            return {"admin_scope": tenant_id or "all", "registered_users": users}
    except Exception:
        pass
    users = [u for u in USERS if u["tenant_id"] == tenant_id] if tenant_id else list(USERS)
    return {"admin_scope": tenant_id or "all", "registered_users": users}


def query_users(arg1: str | None = None, arg2: str | None = None, *args, **kwargs):
    """Returns users from MongoDB collection, with in-memory fallback."""
    tenant_id = None
    if arg2 is not None and isinstance(arg2, str) and arg2.startswith("tenant_"):
        tenant_id = arg2
    elif arg1 is not None and isinstance(arg1, str) and arg1.startswith("tenant_"):
        tenant_id = arg1

    try:
        from app.db.mongo import get_db
        db = get_db()
        if db is not None:
            q = {"tenant_id": tenant_id} if tenant_id else {}
            u_list = list(db.users.find(q, {"_id": 0}))
            if u_list:
                return u_list
    except Exception:
        pass
    if tenant_id:
        return [u for u in USERS if u["tenant_id"] == tenant_id]
    return list(USERS)


TOOLS = {"get_user": get_user, "search_users": search_users,
         "query_users": query_users,
         "get_environment": get_environment, "get_database_schema": get_database_schema,
         "query_demo_database": query_demo_database,
         "get_application_config": get_application_config,
         "get_admin_resource": get_admin_resource}
