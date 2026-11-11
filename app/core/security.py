from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    """Hash a plaintext password using the recommended hasher """
    return password_hash.hash(password)

def verify_password(
        plain_password: str,
        hashed_password: str,
) -> bool:
    """Verify a plaintext password against a hashed password"""
    return password_hash.verify(plain_password, hashed_password)

def create_access_token(user_id: int) -> str:
    """Create a signed jwt access token for a user"""
    now = datetime.now(UTC)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(
           minutes = settings.jwt_access_token_expire_minutes
        ),
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify a JWT access token and return its claims."""
    payload = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[JWT_ALGORITHM],
        options={
            "require": ["sub", "iat", "exp"],
        },
    )

    subject = payload["sub"]

    if not isinstance(subject, str) or not subject.isdecimal():
        raise ValueError("Invalid token subject")

    user_id = int(subject)

    if user_id <= 0:
        raise ValueError("Invalid token subject")

    return payload