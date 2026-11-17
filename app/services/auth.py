import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyRegisteredError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserLogin, UserRegister

#Generate once at appliocation startup
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))

def register_user(db: Session, registration: UserRegister) -> User:
    user = User(
        email=str(registration.email),
        password_hash=hash_password(registration.password),
        display_name=registration.display_name,
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "uq_users_email":
            raise EmailAlreadyRegisteredError from exc

        raise

    db.refresh(user)

    return user

def authenticate_user(
        db: Session,
        credentials: UserLogin,
) -> User | None:
    user = db.scalar(
        select(User).where(User.email == str(credentials.email))
    )
    if user is None:
       verify_password(credentials.password, DUMMY_PASSWORD_HASH)
       return None
    if not verify_password(credentials.password, user.password_hash):
        return None
    return user