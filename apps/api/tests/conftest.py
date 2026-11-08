import os

os.environ["SHIFT_DEMO_MODE"] = "true"
os.environ["SHIFT_ENVIRONMENT"] = "local"
import pytest
from fastapi.testclient import TestClient
from shift_api.database import Base, get_db
from shift_api.main import app
from shift_api.seed import seed
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        seed(session)
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from shift_api import auth
from shift_api.config import settings


@pytest.fixture
def signing(monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "database_url", "postgresql+psycopg://unused")
    monkeypatch.setattr(settings, "supabase_url", "https://fictional.supabase.co")
    monkeypatch.setattr(
        auth,
        "jwks_client",
        lambda _: SimpleNamespace(
            get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private.public_key())
        ),
    )

    def token(**changes):
        claims = dict(
            sub="demo:manager",
            iss=settings.issuer,
            aud="authenticated",
            iat=datetime.now(timezone.utc),
            exp=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        claims.update(changes)
        return jwt.encode(claims, private, algorithm="RS256", headers={"kid": "test"})

    return token
