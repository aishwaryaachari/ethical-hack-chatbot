from fastapi import APIRouter
from pydantic import BaseModel
from app.agents import pipeline_attack1

router = APIRouter(prefix="/api/attack1", tags=["attack1"])


class Attack1In(BaseModel):
    prompt: str
    user_id: str = "u_tanush"
    mode: str = "vulnerable"  # vulnerable | protected


@router.post("/simulate")
def simulate(body: Attack1In):
    assert body.mode in ("vulnerable", "protected"), "mode must be vulnerable|protected"
    return pipeline_attack1.run(body.prompt, body.user_id, body.mode)
