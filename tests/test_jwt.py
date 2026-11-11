from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    JWT_ALGORITHM,
    decode_access_token,
)


def test_decode_access_token_rejects_missing_claims():
    token = jwt.encode(
        {"sub": "42"},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)


def test_decode_access_token_rejects_unexpected_algorithm():
    token = jwt.encode(
        {
            "sub": "42",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS384",
    )

    with pytest.raises(jwt.InvalidAlgorithmError):
        decode_access_token(token)


@pytest.mark.parametrize(
    "subject",
    ["", "abc", "0", "-5", "1.5"],
)
def test_decode_access_token_rejects_invalid_subject(subject: str):
    token = jwt.encode(
        {
            "sub": subject,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(ValueError):
        decode_access_token(token)