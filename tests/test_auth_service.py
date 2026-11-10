from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User
from app.schemas.user import UserRegister
from app.services.auth import EmailAlreadyRegistered, register_user


def test_register_user_creates_user(db_session: Session):
    registration = UserRegister(
        email="  TEST@example.com  ",
        password="a-long-test-password",
        display_name="  Test User  ",
    )

    user = register_user(db_session, registration)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.display_name == "Test User"
    assert user.created_at is not None


def test_register_user_stores_hashed_password(db_session: Session):
    password = "a-long-test-password"

    registration = UserRegister(
        email="password@example.com",
        password=password,
        display_name="Password Test",
    )

    user = register_user(db_session, registration)

    assert user.password_hash != password
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password(password, user.password_hash)


def test_register_user_rejects_duplicate_email(db_session: Session):
    registration = UserRegister(
        email="duplicate@example.com",
        password="a-long-test-password",
        display_name="Original User",
    )

    original_user = register_user(db_session, registration)

    duplicate_registration = UserRegister(
        email="duplicate@example.com",
        password="another-long-test-password",
        display_name="Duplicate User",
    )

    try:
        register_user(db_session, duplicate_registration)
        assert False, "Expected EmailAlreadyRegistered"
    except EmailAlreadyRegistered:
        pass

    existing_user = db_session.get(User, original_user.id)

    assert existing_user is not None
    assert existing_user.email == "duplicate@example.com"
    assert existing_user.display_name == "Original User"


def test_register_user_session_recovers_after_duplicate(
    db_session: Session,
):
    first_registration = UserRegister(
        email="recovery@example.com",
        password="a-long-test-password",
        display_name="First User",
    )

    register_user(db_session, first_registration)

    duplicate_registration = UserRegister(
        email="recovery@example.com",
        password="another-long-test-password",
        display_name="Duplicate User",
    )

    try:
        register_user(db_session, duplicate_registration)
        assert False, "Expected EmailAlreadyRegistered"
    except EmailAlreadyRegistered:
        pass

    next_registration = UserRegister(
        email="after-error@example.com",
        password="a-long-test-password",
        display_name="After Error",
    )

    next_user = register_user(db_session, next_registration)

    assert next_user.id is not None
    assert next_user.email == "after-error@example.com"