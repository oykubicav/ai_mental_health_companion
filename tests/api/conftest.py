"""Shared pytest fixtures for API tests.

All API tests run against the FastAPI TestClient with:
  - LLM provider forced to `mock` (no API key needed)
  - Embedding backend forced to TF-IDF (no ST download)
  - DB set to SQLite in-memory (no Postgres needed)
  - Schema created via SQLAlchemy metadata (skip Alembic in tests)
"""

from __future__ import annotations

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def _env():
    """Force test config before ANY api/pipeline import."""
    os.environ["CBT_LLM_PROVIDER"] = "mock"
    os.environ["CBT_PREFER_ST"] = "0"
    os.environ["CBT_DB_URL"] = "sqlite:///:memory:"
    os.environ["CBT_HASH_SALT"] = "test-salt"
    os.environ["CBT_POLICY_VERSION"] = "0.2"
    os.environ["CBT_JWT_SECRET"] = "test-only-jwt-secret-at-least-32-chars-long"
    # TestClient http://testserver üzerinden konuşuyor; Secure çerezler
    # http'de geri gönderilmiyor. Üretimdeki varsayılan 1 ve orada Secure
    # zorunlu — bunu test_cookie_secure_defaults_on doğruluyor.
    os.environ["CBT_COOKIE_SECURE"] = "0"
    yield


@pytest.fixture(scope="session")
def app(_env):
    """Import the app AFTER env is set, then create schema."""
    from pipeline import composer as _composer
    _composer.register_composer_mocks()
    from api import db as _db
    _db.init_engine()          # bind engine to sqlite:///:memory:
    _db.create_all_for_tests() # CREATE TABLE ...
    from api.main import app as _app
    return _app


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_db(app):
    """Between tests, wipe the tables so each test starts clean.

    Use explicit table order (child → parent) rather than sorted_tables
    because our schema has a nullable FK cycle (sessions ↔ consent_records).
    """
    from api import db as _db
    from api.db.models import (
        Feedback, Turn, Assessment, UserProfile, ConsentRecord, ChatSession,
        RefreshToken, ExerciseEntry, JournalEntry, User,
    )
    engine = _db.get_engine()
    # SQLite'ta foreign key cascade varsayılan olarak kapalı, o yüzden
    # çocuk tablolar açıkça listeleniyor. Yeni tablo eklediğinde buraya da ekle.
    order = [
        Feedback, Turn, Assessment, UserProfile, ConsentRecord, ChatSession,
        RefreshToken, ExerciseEntry, JournalEntry, User,
    ]
    with engine.begin() as conn:
        for model in order:
            conn.execute(model.__table__.delete())
    yield
