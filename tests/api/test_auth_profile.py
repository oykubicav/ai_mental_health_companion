"""Hesap düzeyi onboarding tercihleri — /auth/me/profile.

Ad ve konu seçimi eskiden localStorage'daydı; geçici bir ağ hatası
kullanıcıyı düşürdüğünde profil siliniyor ve onboarding her girişte
tekrar çıkıyordu. Artık hesapta duruyor.
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
    email = f"p{uuid.uuid4().hex[:8]}@test.com"
    uid = _make_user(email)
    r = client.post("/auth/login", json={"email": email, "password": "parola12345"})
    assert r.status_code == 200, r.text
    return {
        "uid": uid,
        "email": email,
        "headers": {"Authorization": f"Bearer {r.json()['access_token']}"},
    }


def test_profile_requires_auth(client):
    assert client.patch("/auth/me/profile", json={"display_name": "x"}).status_code == 401


def test_new_user_not_onboarded(client, auth):
    me = client.get("/auth/me", headers=auth["headers"]).json()
    assert me["onboarded_at"] is None
    assert me["display_name"] is None
    assert me["focus_topics"] == []


def test_save_name_and_topics(client, auth):
    r = client.patch(
        "/auth/me/profile",
        json={"display_name": "Öykü", "focus_topics": ["anxiety", "sleep"]},
        headers=auth["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "Öykü"
    assert body["focus_topics"] == ["anxiety", "sleep"]
    assert body["onboarded_at"] is not None

    # /auth/me üzerinden de kalıcı
    me = client.get("/auth/me", headers=auth["headers"]).json()
    assert me["display_name"] == "Öykü"
    assert me["onboarded_at"] == body["onboarded_at"]


def test_skip_still_marks_onboarded(client, auth):
    """'Şimdilik geç' — ad ve konu yok ama bir daha sorulmamalı."""
    r = client.patch("/auth/me/profile", json={}, headers=auth["headers"])
    assert r.status_code == 200
    assert r.json()["onboarded_at"] is not None
    assert r.json()["display_name"] is None


def test_onboarded_at_not_overwritten(client, auth):
    ilk = client.patch(
        "/auth/me/profile", json={"display_name": "A"}, headers=auth["headers"]
    ).json()["onboarded_at"]

    ikinci = client.patch(
        "/auth/me/profile", json={"display_name": "B"}, headers=auth["headers"]
    ).json()

    assert ikinci["onboarded_at"] == ilk
    assert ikinci["display_name"] == "B"


def test_unknown_topics_dropped(client, auth):
    r = client.patch(
        "/auth/me/profile",
        json={"focus_topics": ["anxiety", "uydurma", "<script>"]},
        headers=auth["headers"],
    )
    assert r.json()["focus_topics"] == ["anxiety"]


def test_blank_name_becomes_null(client, auth):
    r = client.patch(
        "/auth/me/profile", json={"display_name": "   "}, headers=auth["headers"]
    )
    assert r.json()["display_name"] is None


def test_name_length_rejected(client, auth):
    r = client.patch(
        "/auth/me/profile", json={"display_name": "a" * 61}, headers=auth["headers"]
    )
    assert r.status_code == 422


def test_profile_survives_relogin(client, auth):
    """Asıl hata buydu: çıkış-giriş sonrası onboarding tekrar çıkıyordu."""
    client.patch(
        "/auth/me/profile",
        json={"display_name": "Öykü", "focus_topics": ["mood"]},
        headers=auth["headers"],
    )

    r = client.post(
        "/auth/login", json={"email": auth["email"], "password": "parola12345"}
    )
    yeni = {"Authorization": f"Bearer {r.json()['access_token']}"}

    me = client.get("/auth/me", headers=yeni).json()
    assert me["display_name"] == "Öykü"
    assert me["focus_topics"] == ["mood"]
    assert me["onboarded_at"] is not None


def test_focus_greeted_starts_empty(client, auth):
    me = client.get("/auth/me", headers=auth["headers"]).json()
    assert me["focus_greeted_at"] is None


def test_focus_greeted_stamped_once(client, auth):
    """Konular karşılamada bir kez anılır; damga sonradan ileri taşınmaz."""
    client.patch(
        "/auth/me/profile",
        json={"focus_topics": ["anxiety", "work"]},
        headers=auth["headers"],
    )

    ilk = client.patch(
        "/auth/me/profile", json={"focus_greeted": True}, headers=auth["headers"]
    ).json()["focus_greeted_at"]
    assert ilk is not None

    ikinci = client.patch(
        "/auth/me/profile", json={"focus_greeted": True}, headers=auth["headers"]
    ).json()["focus_greeted_at"]
    assert ikinci == ilk


def test_focus_greeted_survives_relogin(client, auth):
    """Asıl şikayet: her yeni sohbette aynı 'şunları demiştin' cümlesi."""
    client.patch(
        "/auth/me/profile",
        json={"focus_topics": ["anxiety"], "focus_greeted": True},
        headers=auth["headers"],
    )

    r = client.post(
        "/auth/login", json={"email": auth["email"], "password": "parola12345"}
    )
    yeni = {"Authorization": f"Bearer {r.json()['access_token']}"}

    me = client.get("/auth/me", headers=yeni).json()
    assert me["focus_greeted_at"] is not None
    assert me["focus_topics"] == ["anxiety"]


def test_focus_greeted_false_does_not_stamp(client, auth):
    r = client.patch(
        "/auth/me/profile", json={"focus_greeted": False}, headers=auth["headers"]
    )
    assert r.json()["focus_greeted_at"] is None


def test_profile_isolated_between_users(client, auth):
    client.patch(
        "/auth/me/profile", json={"display_name": "Öykü"}, headers=auth["headers"]
    )

    other_email = f"o{uuid.uuid4().hex[:8]}@test.com"
    _make_user(other_email)
    r = client.post(
        "/auth/login", json={"email": other_email, "password": "parola12345"}
    )
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}

    me = client.get("/auth/me", headers=other).json()
    assert me["display_name"] is None
    assert me["onboarded_at"] is None


def test_therapy_experience_saved(client, auth):
    r = client.patch(
        "/auth/me/profile", json={"therapy_experience": "ongoing"}, headers=auth["headers"]
    )
    assert r.status_code == 200
    assert r.json()["therapy_experience"] == "ongoing"
    assert client.get("/auth/me", headers=auth["headers"]).json()["therapy_experience"] == "ongoing"


def test_therapy_experience_unknown_value_dropped(client, auth):
    r = client.patch(
        "/auth/me/profile", json={"therapy_experience": "expert"}, headers=auth["headers"]
    )
    assert r.status_code == 200
    assert r.json()["therapy_experience"] is None


def test_therapy_experience_untouched_when_absent(client, auth):
    client.patch("/auth/me/profile", json={"therapy_experience": "some"}, headers=auth["headers"])
    r = client.patch("/auth/me/profile", json={"display_name": "Ada"}, headers=auth["headers"])
    assert r.json()["therapy_experience"] == "some"
