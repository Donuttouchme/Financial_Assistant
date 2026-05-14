from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["heartbeat"])


@router.post("/heartbeat")
def heartbeat() -> dict[str, bool]:
    return {"ok": True}
