"""Integration tests against a database named by DATABASE_URL."""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("Set DATABASE_URL to run database integration tests")
    from app.main import app

    with TestClient(app) as c:
        yield c


def new_email():
    return f"test-{uuid4().hex}@example.com"


def register(client, email, password="Password1!"):
    return client.post("/auth/register", json={"email": email, "password": password})


def login(client, email, password="Password1!"):
    return client.post("/auth/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_and_duplicate(client):
    email = new_email()
    first = register(client, email)
    assert first.status_code == 201
    assert first.json()["email"] == email
    assert isinstance(first.json()["id"], int)
    assert "password_hash" not in first.json()
    assert register(client, email).status_code == 409


def test_invalid_requests(client):
    assert register(client, "not-an-email").status_code == 422
    assert register(client, new_email(), "invalid").status_code == 422
    assert login(client, "invalid").status_code == 422


def test_login_and_logout(client):
    email = new_email()
    assert register(client, email).status_code == 201
    assert login(client, email, "WrongPassword1!").status_code == 401
    assert login(client, new_email()).status_code == 401

    response = login(client, email.upper())
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    token = response.json()["access_token"]
    assert len(token) > 30

    assert client.post("/auth/logout").status_code == 401
    assert client.post("/auth/logout", headers=bearer("invalid")).status_code == 401
    assert client.post("/auth/logout", headers=bearer(token)).status_code == 204
    assert client.post("/auth/logout", headers=bearer(token)).status_code == 401


def test_password_change_revokes_sessions(client):
    email = new_email()
    assert register(client, email).status_code == 201
    token1 = login(client, email).json()["access_token"]
    token2 = login(client, email).json()["access_token"]

    endpoint = "/auth/password/change"
    payload = {"current_password": "Password1!", "new_password": "NewPassword2!"}
    assert client.post(endpoint, json=payload).status_code == 401
    assert client.post(endpoint, json=payload, headers=bearer("fake")).status_code == 401
    assert client.post(
        endpoint,
        json={"current_password": "WrongPassword1!", "new_password": "NewPassword2!"},
        headers=bearer(token1),
    ).status_code == 401
    assert client.post(
        endpoint,
        json={"current_password": "Password1!", "new_password": "invalid"},
        headers=bearer(token1),
    ).status_code == 422

    assert client.post(endpoint, json=payload, headers=bearer(token1)).status_code == 204
    assert client.post("/auth/logout", headers=bearer(token1)).status_code == 401
    assert client.post("/auth/logout", headers=bearer(token2)).status_code == 401
    assert login(client, email).status_code == 401
    assert login(client, email, "NewPassword2!").status_code == 200
