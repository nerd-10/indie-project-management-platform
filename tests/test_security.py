from app.core.security import hash_password, verify_password


def test_hash_password_does_not_store_plaintext():
    password = "A_strong_password_123!"

    hashed_password = hash_password(password)
    
    assert hashed_password != password
    assert hashed_password.startswith("$argon2id$")

def test_verify_password_accepts_correct_password():
    password = "A_strong_password_123!"
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True

def test_verify_password_rejects_incorrect_password():
    hashed_password = hash_password("A_strong_password_123!")

    assert verify_password("Wrong-password-123!", hashed_password) is False

def test_same_password_produces_different_hashes():
    password = "A_strong_password_123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash    