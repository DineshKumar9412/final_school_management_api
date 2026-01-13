# api/users.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import Query
from database.session import get_db
from models.user import User
from schemas.user import UserRead, UserCreate
from response.result import Result
from database.redis_cache import RedisCache

router = APIRouter()

# Redis Catche
cache = RedisCache()

@router.get("/")
async def get_users():
    return Result(200, "SUCCESS", {"detail": "School App Working Fine"}).http_response()

@router.post("/post_test/")
async def post_api_check(item: UserCreate, db: AsyncSession = Depends(get_db)):
    return Result(200, "SUCCESS", {"detail": "Post check successfully", "post_vaue": item.model_dump()}
                  ).http_response()

@router.get("/get_test/")
async def get_api_check(name: str = Query(...), email: str = Query(...)):
    return Result(200, "SUCCESS", {"detail": "get check successfully", "name": name, "email": email}
                  ).http_response()

# Database Insert Check
@router.post("/database_insert_post/")
async def post_api_check(item: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(name=item.name, email=item.email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return Result(200,"SUCCESS",{"detail": "Data insert successfully", "insert_vaue": item.model_dump()}).http_response()

# Database Get Check
@router.get("/database_row_get/", response_model=dict)
async def database_value_user(name: str = Query(...),email: str = Query(...),db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(and_(User.name == name, User.email == email))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return Result(400, "FAILED", {"message": "Record Not Found"}).http_response()
    return Result(200,"SUCCESS",{"id": user.id, "name": user.name, "email": user.email}).http_response()

@router.get("/cache_row_get/", response_model=dict)
async def cache_value_user(name: str = Query(...),email: str = Query(...),db: AsyncSession = Depends(get_db)):

    cache_key = f"user:{name}_{email}"

    cached_user = await cache.get(cache_key)
    if cached_user:
        return Result(200, "SUCCESS (from cache)", cached_user).http_response()

    stmt = select(User).where(and_(User.name == name, User.email == email))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return Result(400, "FAILED", {"detail": "Record Not Found"}).http_response()

    user_data = {"id": user.id, "name": user.name, "email": user.email}

    await cache.set(cache_key, user_data, expire=300)
    return Result(200, "SUCCESS", user_data).http_response()

@router.post("/encryption_check/")
async def post_users_value(item: UserCreate, db: AsyncSession = Depends(get_db)):
    return Result(200, "success", item.model_dump()
                  ).http_response()

@router.get("/decryption_check/")
def get_value(name: str = Query(...), email: str = Query(...)):
    return Result(200, "success", {"name": name, "email": email}
                  ).http_response()
