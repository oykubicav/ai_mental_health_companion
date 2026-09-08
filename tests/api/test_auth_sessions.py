"""Kullanıcının sohbet geçmişi uçları — /auth/sessions.

Sohbet geçmişi projedeki en hassas veri. Buradaki testlerin yarısı
erişim kontrolü: yetkisiz istek, başkasının oturumu, anonim oturumun
sızması, bozuk uuid.
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
    """Doğrulanmış kullanıcı + Authorization başlığı."""
    email = f"u{uuid.uuid4().hex[:8]}@test.com"
    uid = _make_user(email)
    r = client.post("/auth/login", json={"email": email, "password": "parola12345"})
    assert r.status_code == 200, r.text
    return {
        "uid": uid,
        "headers": {"Authorization": f"Bearer {r.json()['access_token']}"},
    }


def test_sessions_requires_auth(client):
    assert client.get("/auth/sessions").status_code == 401


def test_empty_session_list(client, auth):
    r = client.get("/auth/sessions", headers=auth["headers"])
    assert r.status_code == 200
    assert r.json()["sessions"] == []


def test_list_and_detail(client, auth):
    from api.session import get_store
    store = get_store()

    sid = store.new_session()
    store.attach_user(sid, auth["uid"])
    store.append_turn(sid, "Bugün moralim bozuk", "Anlıyorum.", "cbt_support", "depression")
    store.append_turn(sid, "Neden böyle oluyor", "Şöyle...", "cbt_support", "depression")

    body = client.get("/auth/sessions", headers=auth["headers"]).json()
    assert body["total"] == 1
    item = body["sessions"][0]
    assert item["session_id"] == sid
    assert item["turn_count"] == 2
    assert item["title"] == "Bugün moralim bozuk"

    d = client.get(f"/auth/sessions/{sid}", headers=auth["headers"]).json()
    assert len(d["turns"]) == 2
    assert d["turns"][0]["user_message"] == "Bugün moralim bozuk"
    assert d["turns"][0]["response"] == "Anlıyorum."


def test_long_title_is_truncated(client, auth):
    from api.session import get_store
    store = get_store()

    uzun = "Bugün sabahtan beri içimde bir sıkışma var ve nereden geldiğini çıkaramıyorum"
    sid = store.new_session()
    store.attach_user(sid, auth["uid"])
    store.append_turn(sid, uzun, "cevap", "cbt_support", "unknown")

    title = client.get("/auth/sessions", headers=auth["headers"]).json()["sessions"][0]["title"]
    assert len(title) <= 60
    assert title.endswith("…")


def test_cannot_read_other_users_session(client, auth):
    from api.session import get_store
    store = get_store()

    other_uid = _make_user(f"other{uuid.uuid4().hex[:6]}@test.com")
    sid = store.new_session()
    store.attach_user(sid, other_uid)
    store.append_turn(sid, "gizli", "cevap", "cbt_support", "unknown")

    assert client.get(f"/auth/sessions/{sid}", headers=auth["headers"]).status_code == 404
    assert client.delete(f"/auth/sessions/{sid}", headers=auth["headers"]).status_code == 404
    assert client.get("/auth/sessions", headers=auth["headers"]).json()["total"] == 0


def test_anonymous_session_not_listed(client, auth):
    from api.session import get_store
    store = get_store()

    sid = store.new_session()
    store.append_turn(sid, "anonim", "cevap", "cbt_support", "unknown")

    assert client.get("/auth/sessions", headers=auth["headers"]).json()["total"] == 0
    assert client.get(f"/auth/sessions/{sid}", headers=auth["headers"]).status_code == 404


def test_delete_own_session(client, auth):
    from api.session import get_store
    store = get_store()

    sid = store.new_session()
    store.attach_user(sid, auth["uid"])
    store.append_turn(sid, "silinecek", "cevap", "cbt_support", "unknown")

    assert client.delete(f"/auth/sessions/{sid}", headers=auth["headers"]).status_code == 200
    assert client.get("/auth/sessions", headers=auth["headers"]).json()["total"] == 0
    assert store.get_session(sid) is None


def test_empty_session_excluded_from_list(client, auth):
    """Tur eklenmemiş oturum listede görünmemeli."""
    from api.session import get_store
    store = get_store()

    sid = store.new_session()
    store.attach_user(sid, auth["uid"])

    assert client.get("/auth/sessions", headers=auth["headers"]).json()["sessions"] == []


def test_ordering_newest_first(client, auth):
    from api.session import get_store
    store = get_store()

    first = store.new_session()
    store.attach_user(first, auth["uid"])
    store.append_turn(first, "eski sohbet", "cevap", "cbt_support", "unknown")

    second = store.new_session()
    store.attach_user(second, auth["uid"])
    store.append_turn(second, "yeni sohbet", "cevap", "cbt_support", "unknown")

    sessions = client.get("/auth/sessions", headers=auth["headers"]).json()["sessions"]
    assert [s["session_id"] for s in sessions] == [second, first]


def test_bad_uuid_returns_404(client, auth):
    assert client.get("/auth/sessions/not-a-uuid", headers=auth["headers"]).status_code == 404


def test_empty_sessions_are_hidden(client, auth):
    """Mesajsız oturum "Sohbetlerim"de görünmemeli.

    Ölçüm gibi yan işlemler için açılmış boş sohbetler, kullanıcıya hiç
    yapmadığı bir konuşma olarak görünüyordu.
    """
    from api.session import get_store
    store = get_store()

    bos = store.new_session()
    store.attach_user(bos, auth["uid"])

    dolu = store.new_session()
    store.attach_user(dolu, auth["uid"])
    store.append_turn(dolu, "merhaba", "Hoş geldin.", "cbt_support", "unknown")

    body = client.get("/auth/sessions", headers=auth["headers"]).json()
    assert body["total"] == 1
    assert [s["session_id"] for s in body["sessions"]] == [dolu]


def test_current_session_none_when_no_chats(client, auth):
    body = client.get("/auth/sessions/current", headers=auth["headers"]).json()
    assert body["session_id"] is None


def test_current_session_requires_auth(client):
    assert client.get("/auth/sessions/current").status_code == 401


def test_current_session_returns_latest_active(client, auth):
    """Cihazda oturum kimliği olmasa da sunucu devam edilecek sohbeti bilir."""
    from api.session import get_store
    store = get_store()

    from datetime import datetime, timedelta, timezone
    from api import db as _db
    from api.db.models import Turn

    eski = store.new_session()
    store.attach_user(eski, auth["uid"])
    store.append_turn(eski, "ilk", "cevap", "cbt_support", "unknown")

    # Damgalar saniye çözünürlüğünde; iki sohbeti açıkça ayır.
    with _db.get_sessionmaker()() as s, s.begin():
        for t in s.query(Turn).all():
            t.ts = datetime.now(timezone.utc) - timedelta(minutes=30)

    yeni = store.new_session()
    store.attach_user(yeni, auth["uid"])
    store.append_turn(yeni, "ikinci", "cevap", "cbt_support", "unknown")

    body = client.get("/auth/sessions/current", headers=auth["headers"]).json()
    assert body["session_id"] == yeni
    assert body["turn_count"] == 1


def test_current_session_closes_after_sitting_gap(client, auth):
    """Son mesajın üzerinden bir oturuş boşluğu geçtiyse sohbet kapanmıştır."""
    from datetime import datetime, timedelta, timezone
    from api import db as _db
    from api.db.models import Turn
    from api.session import get_store, SITTING_GAP_SECONDS

    store = get_store()
    sid = store.new_session()
    store.attach_user(sid, auth["uid"])
    store.append_turn(sid, "dün", "cevap", "cbt_support", "unknown")

    eski_zaman = datetime.now(timezone.utc) - timedelta(seconds=SITTING_GAP_SECONDS + 60)
    with _db.get_sessionmaker()() as s, s.begin():
        for t in s.query(Turn).all():
            t.ts = eski_zaman

    body = client.get("/auth/sessions/current", headers=auth["headers"]).json()
    assert body["session_id"] is None


def test_current_session_ignores_other_users(client, auth):
    other = _make_user(f"x{uuid.uuid4().hex[:8]}@test.com")
    from api.session import get_store
    store = get_store()
    sid = store.new_session()
    store.attach_user(sid, other)
    store.append_turn(sid, "başkası", "cevap", "cbt_support", "unknown")

    assert client.get("/auth/sessions/current", headers=auth["headers"]).json()["session_id"] is None
