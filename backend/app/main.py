"""One-command entry:  python -m uvicorn app.main:app --reload  (from backend/)"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_attacks, routes_rag, routes_dashboard
from app.db.mongo import seed_if_empty

app = FastAPI(title="AI Security Lab (synthetic, isolated)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(routes_attacks.router)
app.include_router(routes_rag.router)
app.include_router(routes_dashboard.router)


@app.on_event("startup")
def _startup():
    print(seed_if_empty())


@app.get("/")
def root():
    return {"service": "AI Security Lab", "synthetic_only": True,
            "endpoints": ["/api/attack1/simulate", "/api/rag/upload", "/api/rag/query",
                          "/api/events", "/api/dashboard/stats"]}
