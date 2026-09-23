"""Audit log: in-memory ring buffer + optional Mongo persistence."""
from datetime import datetime, timezone

_events: list = []


def log(event_type: str, severity: str, summary: str, details: dict | None = None) -> dict:
    evt = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "type": event_type, "severity": severity, "summary": summary,
           "details": details or {}}
    _events.append(evt)
    if len(_events) > 500:
        del _events[:len(_events) - 500]
    try:
        from app.db.mongo import get_db
        db = get_db()
        if db is not None:
            db.security_events.insert_one(dict(evt))
    except Exception:
        pass
    return evt


def recent(limit: int = 100) -> list:
    return list(reversed(_events[-limit:]))


def stats() -> dict:
    total = len(_events)
    blocked = sum(1 for e in _events if "BLOCK" in e["summary"].upper() or "DENIED" in str(e["details"]).upper())
    return {"total_attacks": sum(1 for e in _events if "attack" in e["type"].lower()),
            "blocked_attacks": blocked,
            "successful_simulations": sum(1 for e in _events if "SIMULATED SUCCESS" in e["summary"]),
            "injection_attempts": sum(1 for e in _events if "njection" in e["summary"]),
            "protected_resources": 7, "security_events": total}
