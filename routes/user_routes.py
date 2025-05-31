from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.user_models import SessionLocal
from repository.user_repository import UserRepository
from schemas.user_schemas import UserThread as UserThreadSchema

router = APIRouter()


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/thread/{user_id}", response_model=Optional[UserThreadSchema])
def get_user_thread_endpoint(user_id: str, db: Session = Depends(get_db)):
    repo = UserRepository(db=db)
    user_thread_orm = repo.get_user_thread(user_id=user_id)
    if not user_thread_orm:
        raise HTTPException(status_code=404, detail="User thread not found")
    return user_thread_orm
