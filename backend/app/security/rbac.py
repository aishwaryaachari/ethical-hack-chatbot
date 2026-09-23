"""Role-based access control + tenant isolation for synthetic tools."""
from typing import Optional

# tool -> minimum role + admin_only resources
TOOL_POLICY = {
    "get_user": {"roles": ["viewer", "editor", "admin"]},
    "search_users": {"roles": ["viewer", "editor", "admin"]},
    "query_users": {"roles": ["viewer", "editor", "admin"]},
    "query_demo_database": {"roles": ["viewer", "editor", "admin"]},
    "get_database_schema": {"roles": ["editor", "admin"]},
    "get_application_config": {"roles": ["admin"]},
    "get_environment": {"roles": ["admin"]},
    "get_admin_resource": {"roles": ["admin"]},
}

ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2}


def authorize(tool: str, caller_role: str, caller_tenant: str,
              target_tenant: Optional[str] = None) -> dict:
    policy = TOOL_POLICY.get(tool)
    if not policy:
        return {"allowed": False, "reason": f"tool '{tool}' not in allowlist"}
    if caller_role not in policy["roles"]:
        return {"allowed": False,
                "reason": f"role '{caller_role}' lacks permission for '{tool}' (needs {policy['roles']})"}
    if target_tenant and target_tenant != caller_tenant:
        return {"allowed": False,
                "reason": f"cross-tenant access denied: {caller_tenant} -> {target_tenant}"}
    return {"allowed": True, "reason": "ok"}
