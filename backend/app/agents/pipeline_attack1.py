"""ATTACK 1 pipeline: backend/API injection BEFORE the LLM is reached."""
from datetime import datetime, timezone
from app.security import engine as sec
from app.tools import sandbox_tools as tools
from app.agents import groq_agent
from app.core import audit
from app.db.synthetic_data import USERS

USER_INDEX = {u["user_id"]: u for u in USERS}


def _caller(user_id: str) -> dict:
    try:
        from app.db.mongo import get_db
        db = get_db()
        if db is not None:
            doc = db.users.find_one({"user_id": user_id}, {"_id": 0})
            if doc:
                return doc
    except Exception:
        pass
    return USER_INDEX.get(user_id, {"user_id": user_id, "role": "viewer", "tenant_id": "tenant_acme"})


def _infer_tool(prompt: str) -> tuple[str, str | None]:
    p = prompt.lower()
    hint_tenant = "tenant_globex" if "globex" in p else ("tenant_initech" if "initech" in p else None)
    if "env" in p or "secret" in p or "api_key" in p or "apikey" in p or "database_url" in p or "stripe" in p:
        return "get_environment", hint_tenant
    if "admin" in p or "/admin" in p:
        return "get_admin_resource", hint_tenant
    if "config" in p:
        return "get_application_config", hint_tenant
    if "schema" in p:
        return "get_database_schema", hint_tenant
    if "users" in p or "credential" in p:
        return "query_users", hint_tenant
    if "database" in p or "record" in p:
        return "query_demo_database", hint_tenant
    return "search_users", hint_tenant


def run(prompt: str, user_id: str, mode: str) -> dict:
    caller = _caller(user_id)
    tool, hint_tenant = _infer_tool(prompt)
    target_tenant = hint_tenant or caller["tenant_id"]
    chain = [
        {"node": "INPUT", "label": f"User prompt ({len(prompt)} chars)"},
        {"node": "BACKEND_API", "label": "Backend input handler (pre-LLM)"},
    ]
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if mode == "vulnerable":
        # Vulnerable backend: no validation, tool auto-executes, output fed to LLM as trusted
        fn = tools.TOOLS[tool]
        try:
            if tool in ("get_environment", "get_database_schema", "get_application_config"):
                data = fn()
            elif tool in ("query_demo_database", "get_admin_resource", "query_users"):
                data = fn(target_tenant)
            else:
                data = fn(prompt[:40], caller["tenant_id"])
        except Exception as e:
            data = {"error": str(e)}
        llm = groq_agent.generate(
            prompt,
            context=f"(backend passed raw prompt with NO checks; tool '{tool}' already executed)\nTool output:\n{data}",
            persona="vulnerable")
        chain += [{"node": "LLM", "label": "Groq/sim: trusted raw intent"},
                  {"node": "TOOL", "label": f"{tool} — no auth check"},
                  {"node": "RESOURCE", "label": "synthetic resource LEAKED (demo)"}]
        audit.log("attack1", "CRITICAL", "SIMULATED SUCCESS — backend injection leaked synthetic data",
                  {"mode": mode, "tool": tool, "user": user_id})
        return {"mode": mode, "attack": "Backend/API Injection", "layer": "backend pre-LLM",
                "ai_decision": "TRUSTED RAW INPUT (vulnerable backend)", "tool": tool,
                "authorization": "SKIPPED (vulnerable)", "result": "SIMULATED SUCCESS",
                "data": data, "llm": llm, "chain": chain, "timestamp": ts,
                "warning": "Synthetic demo data only. Vulnerable path shown for education."}

    # Protected: backend validates BEFORE any LLM call
    verdict = sec.evaluate(tool, caller["role"], caller["tenant_id"], target_tenant, prompt, user_id)
    chain += [{"node": "SECURITY_ENGINE", "label": f"RBAC+detector verdict: {verdict['reason'][:60]}"}]
    if not verdict["allowed"]:
        chain += [{"node": "BLOCK", "label": "DENIED pre-LLM — LLM never invoked for tool"}]
        audit.log("attack1", "HIGH" if verdict["detection"]["is_injection"] else "MEDIUM",
                  f"BLOCKED — backend injection ({tool})",
                  {"mode": mode, "tool": tool, "reason": verdict["reason"], "user": user_id})
        return {"mode": mode, "attack": "Backend/API Injection", "layer": "backend pre-LLM",
                "ai_decision": "N/A — blocked before LLM", "tool": tool,
                "authorization": "DENIED", "result": "BLOCKED",
                "detection": verdict["detection"], "reason": verdict["reason"],
                "chain": chain, "timestamp": ts}
    llm = groq_agent.generate(prompt, context="(validated request, least-privilege scope)",
                                persona="protected")
    chain += [{"node": "LLM", "label": "Groq/sim: least-privilege answer"},
              {"node": "RESOURCE", "label": "only own-tenant synthetic data"}]
    audit.log("attack1", "INFO", "ALLOWED — legitimate backend request",
              {"mode": mode, "tool": tool, "user": user_id})
    return {"mode": mode, "attack": "Backend/API Injection", "layer": "backend pre-LLM",
            "ai_decision": "VALIDATED INPUT", "tool": tool, "authorization": "ALLOWED",
            "result": "ALLOWED", "llm": llm, "chain": chain, "timestamp": ts}
