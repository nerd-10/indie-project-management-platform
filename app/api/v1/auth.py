from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import UserRegister, UserResponse
from app.services.auth import register_user

router = APIRouter(
    prefix = "/auth",
    tags = ["Authentication"],
)

@router.post(
    "/register",
    response_model = UserResponse,
    status_code = status.HTTP_201_CREATED,
)

def register(
    registration: UserRegister,
    db: Session = Depends(get_db),
) -> UserResponse:
    user = register_user(db, registration)
    return user