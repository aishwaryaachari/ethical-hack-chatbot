"""Prompt-injection / override detector (regex + keyword heuristics)."""
import re

PATTERNS = [
    r"ignore\s+previous\s+(restrictions|instructions|prompt)",
    r"system\s*override",
    r"treat\s+this\s+document\s+as\s+(an?\s+)?(admin|administrator|system|trusted)",
    r"reveal\s+(protected|secret|configuration|credentials|password)",
    r"do\s+not\s+(mention|disclose|tell).{0,40}instructions?",
    r"as\s+an?\s+admin(istrator)?\s*,?\s*(reveal|show|disclose|bypass)",
    r"email\s+\S+@\S+\s+with\s+.{0,20}password",
    r"(bypass|disable)\s+(auth|restriction|filter|guardrail)",
    r"union\s+select|drop\s+table|--\s*$",
    r"\.onion\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in PATTERNS]

RISKY_KEYWORDS = ["env", "secret", "admin", "/admin", "config", "passwd", "api_key", "apikey"]


def detect(text: str) -> dict:
    text = text or ""
    matched = [pat for pat, rx in zip(PATTERNS, _COMPILED) if rx.search(text)]
    kw = [k for k in RISKY_KEYWORDS if k.lower() in text.lower()]
    score = min(1.0, 0.45 * len(matched) + 0.1 * len(kw))
    level = "NONE" if not matched else ("CRITICAL" if score >= 0.8 else ("HIGH" if score >= 0.45 else "MEDIUM"))
    return {"matched": matched, "keywords": kw, "score": round(score, 2), "level": level,
            "is_injection": bool(matched)}
