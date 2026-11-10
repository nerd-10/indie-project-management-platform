import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from app.core.config import settings


@pytest.fixture(scope="session")
def test_engine() -> Engine:
    base_url = make_url(settings.database_url)

    if base_url.database != "indie_pm_db":
        raise RuntimeError(
            "Tests must derive their database URL from indie_pm_db. "
            "Check DATABASE_URL configuration."
        )

    test_url = base_url.set(database="indie_pm_test_db")

    if test_url.database != "indie_pm_test_db":
        raise RuntimeError("Refusing to connect to an unexpected database.")

    engine = create_engine(
        test_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
    )

    try:
        with engine.connect() as connection:
            database, user = connection.execute(
                text("SELECT current_database(), current_user")
            ).one()

            if database != "indie_pm_test_db":
                raise RuntimeError(
                    f"Expected indie_pm_test_db, connected to {database}"
                )

            print(f"\nTest database: {database}")
            print(f"Test database role: {user}")

        yield engine

    finally:
        engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine):
    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()