from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limiter import SlidingWindowRateLimiter
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.user import TokenResponse, UserLogin, UserRegister, UserResponse
from app.services.auth import authenticate_user, register_user

router = APIRouter(
    prefix = "/auth",
    tags = ["Authentication"],
)

account_login_limiter = SlidingWindowRateLimiter(
    max_attempts=5,
    window_seconds=900.
)

ip_login_limiter = SlidingWindowRateLimiter(
    max_attempts=20,
    window_seconds=900,
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
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    account_key = (str(credentials.email), client_ip)
    ip_key = client_ip

    account_reservation = account_login_limiter.try_acquire(account_key)

    if account_reservation is None:
        retry_after = account_login_limiter.get_retry_after(account_key)

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    ip_reservation = ip_login_limiter.try_acquire(ip_key)

    if ip_reservation is None:
        account_login_limiter.release(account_key, account_reservation)

        retry_after = ip_login_limiter.get_retry_after(ip_key)

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        user = authenticate_user(db, credentials)

    except Exception:
        account_login_limiter.release(account_key, account_reservation)
        ip_login_limiter.release(ip_key, ip_reservation)
        raise

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    account_login_limiter.release(account_key, account_reservation)
    ip_login_limiter.release(ip_key, ip_reservation)

    access_token = create_access_token(user.id)

    return TokenResponse(access_token=access_token)