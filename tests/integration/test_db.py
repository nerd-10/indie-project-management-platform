from sqlalchemy import text
from sqlalchemy.orm import Session


def test_database_session_connects_to_test_database(
    db_session: Session,
):
    database = db_session.execute(
        text("SELECT current_database()")
    ).scalar_one()

    assert database == "indie_pm_test_db"


def test_database_session_uses_application_role(
    db_session: Session,
):
    user = db_session.execute(
        text("SELECT current_user")
    ).scalar_one()

    assert user == "indie_pm_app"


def test_database_session_can_execute_queries(
    db_session: Session,
):
    result = db_session.execute(
        text("SELECT 1")
    ).scalar_one()

    assert result == 1

def test_database_session_rolls_back_committed_test_data(
    db_session: Session,
):
    db_session.execute(
        text(
            """
            INSERT INTO users (email, password_hash, display_name)
            VALUES (
                'rollback-check@example.invalid',
                'temporary-test-hash',
                'Rollback Check'
            )
            """
        )
    )

    db_session.commit()

    user_exists = db_session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM users
                WHERE email = 'rollback-check@example.invalid'
            )
            """
        )
    ).scalar_one()

    assert user_exists is True