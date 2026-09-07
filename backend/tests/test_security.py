import uuid
import pytest
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_operations():
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id)

    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == str(user_id)
    assert "exp" in payload


def test_invalid_jwt_token():
    invalid_token = "invalid.token.value"
    payload = decode_access_token(invalid_token)
    assert payload is None
