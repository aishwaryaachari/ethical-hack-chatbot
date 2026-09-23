"""Mongo connection with graceful in-memory fallback (lab runs without mongod)."""
_client = None
_db = None


def get_db():
    global _client, _db
    if _db is not None:
        return _db
    try:
        from pymongo import MongoClient
        from app.core.config import settings
        _client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=4000)
        _client.admin.command("ping")
        try:
            _db = _client.get_database()
        except Exception:
            _db = _client["demo_lab"]
        return _db
    except Exception:
        return None


def seed_if_empty():
    db = get_db()
    if db is None:
        return {"seeded": False, "reason": "no mongo — using in-memory synthetic data"}
    try:
        from app.db.synthetic_data import TENANTS, USERS
        # Drop stale mock collections from older builds — nothing reads them
        # anymore; every tool queries the REAL users collection below.
        for stale in ("records", "synthetic_secrets"):
            try:
                db[stale].drop()
            except Exception:
                pass
        if db.tenants.count_documents({}) == 0:
            db.tenants.insert_many(TENANTS)
            db.users.insert_many(USERS)
            return {"seeded": True}
        return {"seeded": False, "reason": "already seeded"}
    except Exception as e:
        return {"seeded": False, "reason": str(e)}
