from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserLogin, UserRegister
from app.services.auth import authenticate_user, register_user


def test_authenticate_user_with_valid_credentials(
    db_session: Session,
):
    password = "a-long-test-password"

    registration = UserRegister(
        email="login@example.com",
        password=password,
        display_name="Login Test",
    )

    registered_user = register_user(db_session, registration)

    credentials = UserLogin(
        email="login@example.com",
        password=password,
    )

    authenticated_user = authenticate_user(
        db_session,
        credentials,
    )

    assert authenticated_user is not None
    assert authenticated_user.id == registered_user.id
    assert isinstance(authenticated_user, User)


def test_authenticate_user_with_incorrect_password(
    db_session: Session,
):
    registration = UserRegister(
        email="wrong-password@example.com",
        password="a-long-test-password",
        display_name="Password Test",
    )

    register_user(db_session, registration)

    credentials = UserLogin(
        email="wrong-password@example.com",
        password="an-incorrect-password",
    )

    authenticated_user = authenticate_user(
        db_session,
        credentials,
    )

    assert authenticated_user is None


def test_authenticate_user_with_unknown_email(
    db_session: Session,
):
    credentials = UserLogin(
        email="unknown@example.com",
        password="a-long-test-password",
    )

    authenticated_user = authenticate_user(
        db_session,
        credentials,
    )

    assert authenticated_user is None