from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.user import TokenResponse, UserLogin, UserRegister, UserResponse
from app.services.auth import authenticate_user, register_user

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

@router.post(
    "/login",
    response_model = TokenResponse,
    status_code = status.HTTP_200_OK,
)

def login(
        credentials: UserLogin,
        db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_user(db, credentials)

    if user is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid email or password",
            headers = {"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token = access_token,
    )