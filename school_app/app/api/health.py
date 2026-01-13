from fastapi import APIRouter
from app.database.session import engine

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health():
    return {"db_connected": engine is not None}
