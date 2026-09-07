"""Günlük — /journal.

Gün başına tek kayıt: aynı güne ikinci kez yazmak yeni satır açmaz,
üstüne yazar. Kayıtlar hesaba bağlı ve başkasına görünmez.
"""

import uuid
from datetime import date, timedelta

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
    email = f"g{uuid.uuid4().hex[:8]}@test.com"
    uid = _make_user(email)
    return {"uid": uid, "headers": _login(client, email)}


BUGUN = date.today().isoformat()
DUN = (date.today() - timedelta(days=1)).isoformat()
YARIN = (date.today() + timedelta(days=1)).isoformat()


def test_requires_auth(client):
    assert client.put(f"/journal/{BUGUN}", json={"mood": 3}).status_code == 401
    assert client.get("/journal").status_code == 401


def test_write_and_read_day(client, auth):
    r = client.put(
        f"/journal/{BUGUN}",
        json={
            "mood": 4,
            "did": "Yürüyüşe çıktım",
            "thoughts": "Yine geç kaldım diye kendime kızdım",
            "good": "Kahve iyi geldi",
            "tags": ["hareket", "disari_ciktim"],
        },
        headers=auth["headers"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["entry_date"] == BUGUN
    assert body["mood"] == 4
    assert body["tags"] == ["hareket", "disari_ciktim"]

    assert client.get(f"/journal/{BUGUN}", headers=auth["headers"]).json()["did"] == "Yürüyüşe çıktım"


def test_second_write_overwrites_same_day(client, auth):
    client.put(f"/journal/{BUGUN}", json={"mood": 2, "did": "ilk"}, headers=auth["headers"])
    r = client.put(f"/journal/{BUGUN}", json={"mood": 5}, headers=auth["headers"])
    assert r.status_code == 200
    assert r.json()["mood"] == 5
    # Gönderilmeyen alan silinmez.
    assert r.json()["did"] == "ilk"

    assert len(client.get("/journal", headers=auth["headers"]).json()["entries"]) == 1


def test_days_are_separate_rows(client, auth):
    client.put(f"/journal/{BUGUN}", json={"mood": 3}, headers=auth["headers"])
    client.put(f"/journal/{DUN}", json={"mood": 1}, headers=auth["headers"])

    entries = client.get("/journal", headers=auth["headers"]).json()["entries"]
    assert [e["entry_date"] for e in entries] == [BUGUN, DUN]


def test_future_date_rejected(client, auth):
    assert client.put(f"/journal/{YARIN}", json={"mood": 3}, headers=auth["headers"]).status_code == 422


def test_bad_date_and_missing_day(client, auth):
    assert client.put("/journal/dun", json={"mood": 3}, headers=auth["headers"]).status_code == 422
    assert client.get(f"/journal/{DUN}", headers=auth["headers"]).status_code == 404
    assert client.delete(f"/journal/{DUN}", headers=auth["headers"]).status_code == 404


def test_mood_range_and_unknown_tags(client, auth):
    assert client.put(f"/journal/{BUGUN}", json={"mood": 9}, headers=auth["headers"]).status_code == 422
    r = client.put(
        f"/journal/{BUGUN}", json={"tags": ["hareket", "kediyi_sevdim"]}, headers=auth["headers"]
    )
    assert r.json()["tags"] == ["hareket"]


def test_blank_text_becomes_null(client, auth):
    r = client.put(f"/journal/{BUGUN}", json={"did": "   "}, headers=auth["headers"])
    assert r.json()["did"] is None


def test_delete_day(client, auth):
    client.put(f"/journal/{BUGUN}", json={"mood": 3}, headers=auth["headers"])
    assert client.delete(f"/journal/{BUGUN}", headers=auth["headers"]).status_code == 200
    assert client.get("/journal", headers=auth["headers"]).json()["entries"] == []


def test_journal_isolated_between_users(client, auth):
    other_email = f"o{uuid.uuid4().hex[:8]}@test.com"
    _make_user(other_email)
    other = _login(client, other_email)
    client.put(f"/journal/{BUGUN}", json={"mood": 5, "did": "başkasının günü"}, headers=other)

    assert client.get("/journal", headers=auth["headers"]).json()["entries"] == []
    assert client.get(f"/journal/{BUGUN}", headers=auth["headers"]).status_code == 404
    # Aynı gün iki kullanıcıda ayrı ayrı durabilmeli.
    assert client.put(f"/journal/{BUGUN}", json={"mood": 1}, headers=auth["headers"]).status_code == 200
    assert client.get(f"/journal/{BUGUN}", headers=other).json()["mood"] == 5


def test_first_journal_milestone(client, auth):
    client.put(f"/journal/{BUGUN}", json={"mood": 3}, headers=auth["headers"])
    body = client.get("/auth/me/insights", headers=auth["headers"]).json()
    assert "first_journal" in [m["kind"] for m in body["milestones"]]
