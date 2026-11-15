from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyRegisteredError
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserRegister


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