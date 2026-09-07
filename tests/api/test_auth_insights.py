"""Gelişimim — /auth/me/insights kilometre taşları.

Sayı yok, seri yok: yalnızca ilk'ler. Yönlendirme de saklanmıyor.
"""

import uuid

import pytest


def _make_user(email: str, password: str = "parola12345") -> uuid.UUID:
    from api import db as _db
    from api.db.models import User
    from api.auth.passwords import hash_password

    with _db.get_sessionmaker()() as s, s.begin():
        u = User(email=email, password_hash=hash_password(password), email_verified=True)
        s.add(u)
        s.flush()
        uid = u.id
    return uid


@pytest.fixture()
def auth(client):
    email = f"i{uuid.uuid4().hex[:8]}@test.com"
    uid = _make_user(email)
    r = client.post("/auth/login", json={"email": email, "password": "parola12345"})
    assert r.status_code == 200, r.text
    return {"uid": uid, "headers": {"Authorization": f"Bearer {r.json()['access_token']}"}}


def _kinds(body):
    return [m["kind"] for m in body["milestones"]]


def test_insights_requires_auth(client):
    assert client.get("/auth/me/insights").status_code == 401


def test_no_milestones_for_fresh_user(client, auth):
    body = client.get("/auth/me/insights", headers=auth["headers"]).json()
    assert body["milestones"] == []


def test_first_session_only(client, auth):
    from api.session import get_store
    store = get_store()
    sid = store.new_session()
    store.attach_user(sid, auth["uid"])
    store.append_turn(sid, "merhaba", "Hoş geldin.", "cbt_support", "unknown")

    body = client.get("/auth/me/insights", headers=auth["headers"]).json()
    assert _kinds(body) == ["first_session"]
    assert body["milestones"][0]["at"]


def test_technique_and_helped(client, auth):
    from api import db as _db
    from api.db.models import UserProfile
    from api.session import get_store
    store = get_store()
    sid = store.new_session()
    store.attach_user(sid, auth["uid"])

    with _db.get_sessionmaker()() as s, s.begin():
        s.add(UserProfile(
            session_id=uuid.UUID(sid), user_id=auth["uid"],
            coping_tried={"worry_time": "deneyecek", "diaphragm_breathing": "yararsız"},
        ))

    body = client.get("/auth/me/insights", headers=auth["headers"]).json()
    assert _kinds(body) == ["first_session", "first_technique"]
    assert body["milestones"][1]["detail"] == "Diyafram nefesi"

    sid2 = store.new_session()
    store.attach_user(sid2, auth["uid"])
    with _db.get_sessionmaker()() as s, s.begin():
        s.add(UserProfile(
            session_id=uuid.UUID(sid2), user_id=auth["uid"],
            coping_tried={"thought_record": "yararlı"},
        ))

    body = client.get("/auth/me/insights", headers=auth["headers"]).json()
    assert "first_helped" in _kinds(body)
    yarayan = next(m for m in body["milestones"] if m["kind"] == "first_helped")
    assert yarayan["detail"] == "Düşünce kaydı"


def test_planned_technique_is_not_tried(client, auth):
    from api import db as _db
    from api.db.models import UserProfile
    from api.session import get_store
    store = get_store()
    sid = store.new_session()
    store.attach_user(sid, auth["uid"])
    with _db.get_sessionmaker()() as s, s.begin():
        s.add(UserProfile(
            session_id=uuid.UUID(sid), user_id=auth["uid"],
            coping_tried={"worry_time": "deneyecek"},
        ))
    body = client.get("/auth/me/insights", headers=auth["headers"]).json()
    assert "first_technique" not in _kinds(body)


def test_assessment_and_referral(client, auth):
    from api import db as _db
    from api.db.models import Assessment
    from api.session import get_store
    store = get_store()
    sid = store.new_session()
    store.attach_user(sid, auth["uid"])
    store.append_turn(sid, "çok kötüyüm", "Bir uzmana...", "professional_referral_supportive", "depression")
    with _db.get_sessionmaker()() as s, s.begin():
        s.add(Assessment(
            session_id=uuid.UUID(sid), user_id=auth["uid"], kind="phq9",
            answers=[1] * 9, total_score=9, severity="mild",
        ))

    body = client.get("/auth/me/insights", headers=auth["headers"]).json()
    kinds = _kinds(body)
    assert "first_assessment" in kinds and "first_referral" in kinds
    olcum = next(m for m in body["milestones"] if m["kind"] == "first_assessment")
    assert olcum["detail"] == "PHQ9"


def test_milestones_isolated_between_users(client, auth):
    other = _make_user(f"o{uuid.uuid4().hex[:8]}@test.com")
    from api.session import get_store
    store = get_store()
    sid = store.new_session()
    store.attach_user(sid, other)
    store.append_turn(sid, "x", "y", "cbt_support", "unknown")

    body = client.get("/auth/me/insights", headers=auth["headers"]).json()
    assert body["milestones"] == []
