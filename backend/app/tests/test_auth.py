import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

from app.db import database
from app.main import app
from app.models.user import User


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    database.engine = engine
    database.SessionLocal = TestingSessionLocal
    database.Base.metadata.create_all(bind=engine)
    assert User.__table__ in database.Base.metadata.sorted_tables

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_signup_login_and_me(client):
    signup_payload = {
        "email": "user@example.com",
        "password": "Password123!",
        "full_name": "Test User",
    }

    signup_response = client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201
    assert signup_response.json()["email"] == signup_payload["email"]
    assert signup_response.json()["full_name"] == signup_payload["full_name"]
    assert "hashed_password" not in signup_response.text

    duplicate_response = client.post("/auth/signup", json=signup_payload)
    assert duplicate_response.status_code == 400

    login_response = client.post(
        "/auth/login",
        data={
            "username": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]

    me_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == signup_payload["email"]

    missing_token_response = client.get("/users/me")
    assert missing_token_response.status_code == 401


def test_signup_rejects_weak_password(client):
    response = client.post(
        "/auth/signup",
        json={
            "email": "weak@example.com",
            "password": "password123!",
            "full_name": "Weak User",
        },
    )

    assert response.status_code == 422
    assert "Password must include" in response.text


def test_login_rate_limit_blocks_repeated_failures(client):
    signup_payload = {
        "email": "ratelimit@example.com",
        "password": "Password123!",
        "full_name": "Rate Limit User",
    }
    assert client.post("/auth/signup", json=signup_payload).status_code == 201

    last_response = None
    for _ in range(11):
        last_response = client.post(
            "/auth/login",
            data={"username": signup_payload["email"], "password": "WrongPassword123!"},
        )

    assert last_response is not None
    assert last_response.status_code == 429
    assert "Too many authentication attempts" in last_response.json()["detail"]
