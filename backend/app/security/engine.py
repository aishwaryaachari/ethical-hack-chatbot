"""Security Engine: every tool request passes through here. AI is never trusted."""
import time
from collections import defaultdict
from .detector import detect
from .rbac import authorize

_rate: dict = defaultdict(list)
RATE_LIMIT = 20  # reqs / 60s per user


def check_rate(user_id: str) -> bool:
    now = time.time()
    window = [t for t in _rate[user_id] if now - t < 60]
    _rate[user_id] = window
    if len(window) >= RATE_LIMIT:
        return False
    _rate[user_id].append(now)
    return True


def redact(text: str) -> str:
    if not text:
        return text
    for secret in ["demo_secret_12345", "demo-password", "sk_test_demo_67890",
                   "aws_demo_secret_abcdef", "sso_demo_secret_999"]:
        text = text.replace(secret, "***REDACTED***")
    return text


def evaluate(tool: str, caller_role: str, caller_tenant: str,
             target_tenant: str | None, raw_input: str, user_id: str) -> dict:
    """Returns {allowed, reason, detection} — single choke point."""
    det = detect(raw_input or "")
    if not check_rate(user_id):
        return {"allowed": False, "reason": "rate limit exceeded", "detection": det}
    if det["is_injection"] and det["level"] in ("HIGH", "CRITICAL"):
        return {"allowed": False,
                "reason": f"prompt-injection detected ({det['level']}): {det['matched'][:2]}",
                "detection": det}
    auth = authorize(tool, caller_role, caller_tenant, target_tenant)
    if not auth["allowed"]:
        return {"allowed": False, "reason": auth["reason"], "detection": det}
    return {"allowed": True, "reason": "authorized", "detection": det}
