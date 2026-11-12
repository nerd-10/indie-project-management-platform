
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import JWT_ALGORITHM, create_access_token
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserRegister
from app.services.auth import register_user


def create_credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(
        scheme = "Bearer",
        credentials = token,
    )

def test_get_current_user_rejects_missing_credentials(
        db_session: Session,
):
  with pytest.raises(HTTPException) as exc_info:
     get_current_user(credentials = None, db = db_session)
     assert exc_info.value.status.code == 401
     assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

def test_get_current_user_rejects_invalid_token(
  db_session: Session    
):
   credentials = create_credentials("invalid_token")
   with pytest.raises(HTTPException) as exc_info:
      get_current_user(credentials = credentials, db = db_session)
      assert exc_info.value.status.code == 401

def test_get_currewnt_user_rejects_expired_token(
      db_session: Session
):
   now = datetime.now(UTC)
   token = jwt.encode(
      {
         "sub": "42",
         "iat": now - timedelta(minutes=2),
         "exp": now - timedelta(minutes=1)
      },
      settings.jwt_secret_key.get_secret_value(),
      algorithm = JWT_ALGORITHM,
   )
   credentials = create_credentials(token)
   with pytest.raises(HTTPException) as exc_info:
      get_current_user(credentials = credentials, db = db_session)
      assert exc_info.value.status.code == 401

def test_get_current_user_returns_existing_user(
      db_session: Session
):
   registration = UserRegister(
    email = "auth-dependcy@example.com",
    password = "a-long-test-password",
    display_name = "Authentication Test"
   )

   user = register_user(db_session, registration)
   token = create_access_token(user.id)
   credentials = create_credentials(token)
   current_user = get_current_user(
      credentials = credentials,
      db = db_session,
   )
   assert isinstance(current_user, User)
   assert current_user.id == user.id
   assert current_user.email == user.email

def test_get_current_user_rejects_nonexistent_user(
      db_session: Session
):
   token = create_access_token(user_id = 999999)
   credentials = create_credentials(token)
   with pytest.raises(HTTPException) as exc_info:
      get_current_user(credentials = credentials, db = db_session)
      assert exc_info.value.status.code == 401