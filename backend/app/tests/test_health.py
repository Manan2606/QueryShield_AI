import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

from app.db import database
from app.db.readiness import expected_migration_revision
from app.main import app


def test_database_health_fails_when_schema_tables_are_missing():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    database.engine = engine
    database.SessionLocal = TestingSessionLocal

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/health/db")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "missing tables" in response.json()["detail"]


def test_database_health_passes_when_required_tables_exist():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    database.engine = engine
    database.SessionLocal = TestingSessionLocal
    database.Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
            {"version": expected_migration_revision()},
        )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/health/db")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
        "schema_ready": True,
        "migration_current": True,
    }


def test_readiness_passes_when_schema_and_config_are_ready():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    database.engine = engine
    database.SessionLocal = TestingSessionLocal
    database.Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
            {"version": expected_migration_revision()},
        )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["config_ready"] is True
