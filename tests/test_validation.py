"""Pydantic validation without an external database."""

import pytest
from pydantic import ValidationError

from app.schemas import ChangePasswordRequest, LoginRequest, RegisterRequest


def test_valid_registration():
    data = RegisterRequest(email="User@Example.com", password="Password1!")
    assert data.email == "user@example.com"


@pytest.mark.parametrize(
    "password",
    [
        "Short1!",
        "A" * 22 + "a1!",  # 25 characters
        "password1!",
        "PASSWORD1!",
        "Password!",
        "Password1",
        "Password1@",
        'Password1"',
        "Password1'",
        "Password1<",
        "Password1>",
        "Password1 ",
    ],
)
def test_invalid_registration_password(password):
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password=password)


def test_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(email="wrong-email", password="Password1!")


def test_password_change_validates_new_password():
    with pytest.raises(ValidationError):
        ChangePasswordRequest(current_password="Password1!", new_password="invalid")


def test_login_validates_email_and_nonempty_password():
    assert LoginRequest(email="USER@EXAMPLE.COM", password="Password1!").email == "user@example.com"
    with pytest.raises(ValidationError):
        LoginRequest(email="bad", password="")
