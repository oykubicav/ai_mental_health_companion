"""Egzersiz kayıtları — /exercises.

Kayıt yalnızca hesabı olana; başkasının kaydı görünmez ve silinemez.
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


def _login(client, email):
    r = client.post("/auth/login", json={"email": email, "password": "parola12345"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    email = f"e{uuid.uuid4().hex[:8]}@test.com"
    uid = _make_user(email)
    return {"uid": uid, "headers": _login(client, email)}


THOUGHT = {
    "situation": "Toplantıda sunum",
    "thought": "Herkes saçmaladığımı düşündü",
    "emotion": "utanç",
    "intensity_before": 80,
    "evidence_for": "Biri telefonuna baktı",
    "evidence_against": "İki kişi soru sordu, biri teşekkür etti",
    "alternative": "Bir kişinin dikkati dağılmış olabilir, sunum bitti",
    "intensity_after": 40,
}


def test_requires_auth(client):
    assert client.post("/exercises", json={"kind": "thought_record", "payload": THOUGHT}).status_code == 401
    assert client.get("/exercises").status_code == 401


def test_create_list_delete(client, auth):
    r = client.post("/exercises", json={"kind": "thought_record", "payload": THOUGHT}, headers=auth["headers"])
    assert r.status_code == 201, r.text
    eid = r.json()["id"]
    assert r.json()["payload"]["intensity_after"] == 40

    body = client.get("/exercises", headers=auth["headers"]).json()
    assert [e["id"] for e in body["entries"]] == [eid]

    body = client.get("/exercises?kind=small_step", headers=auth["headers"]).json()
    assert body["entries"] == []

    assert client.delete(f"/exercises/{eid}", headers=auth["headers"]).status_code == 200
    assert client.get("/exercises", headers=auth["headers"]).json()["entries"] == []


def test_unknown_kind_rejected(client, auth):
    r = client.post("/exercises", json={"kind": "yoga", "payload": {}}, headers=auth["headers"])
    assert r.status_code == 422


def test_oversized_payload_rejected(client, auth):
    r = client.post(
        "/exercises", json={"kind": "thought_record", "payload": {"thought": "x" * 7000}},
        headers=auth["headers"],
    )
    assert r.status_code == 413


def test_other_users_entry_hidden_and_undeletable(client, auth):
    other_email = f"o{uuid.uuid4().hex[:8]}@test.com"
    _make_user(other_email)
    other = _login(client, other_email)
    eid = client.post(
        "/exercises", json={"kind": "small_step", "payload": {"plan": "yürüyüş"}}, headers=other
    ).json()["id"]

    assert client.get("/exercises", headers=auth["headers"]).json()["entries"] == []
    assert client.delete(f"/exercises/{eid}", headers=auth["headers"]).status_code == 404
    assert client.get("/exercises", headers=other).json()["entries"][0]["id"] == eid


def test_bad_uuid_is_404(client, auth):
    assert client.delete("/exercises/degil", headers=auth["headers"]).status_code == 404


def test_first_exercise_milestone(client, auth):
    client.post("/exercises", json={"kind": "small_step", "payload": {"plan": "x"}}, headers=auth["headers"])
    body = client.get("/auth/me/insights", headers=auth["headers"]).json()
    m = next(x for x in body["milestones"] if x["kind"] == "first_exercise")
    assert m["detail"] == "small_step"
