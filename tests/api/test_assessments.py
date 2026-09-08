"""PHQ-9 / GAD-7 uçları — /assessments.

Buradaki asıl mesele kapsam: hesabı olan kullanıcının ölçümleri bütün
oturumlarına yayılıyor. Oturuma göre filtrelemek grafiği her yeni
sohbette sıfırlıyordu ve "ilk ölçüm" kilometre taşı hiç tetiklenmiyordu.
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
    email = f"a{uuid.uuid4().hex[:8]}@test.com"
    uid = _make_user(email)
    return {"uid": uid, "headers": _login(client, email)}


@pytest.fixture()
def sid():
    from api.session import get_store
    return get_store().new_session()


# 9. madde (kendine zarar) her ikisinde de 0 — kriz uyarısını ayrı test ediyoruz.
HAFIF = [1] * 8 + [0]    # PHQ-9 toplam 8 → mild
AGIR = [3] * 8 + [0]     # PHQ-9 toplam 24 → severe


def _submit(client, session_id, answers=HAFIF, kind="phq9", headers=None):
    return client.post(
        "/assessments",
        json={"session_id": session_id, "kind": kind, "answers": answers},
        headers=headers or {},
    )


def test_anonymous_submit_and_list(client, sid):
    r = _submit(client, sid)
    assert r.status_code == 200, r.text
    assert r.json()["assessment"]["total_score"] == 8
    assert r.json()["assessment"]["severity"] == "mild"
    assert r.json()["crisis_alert"] is False

    rows = client.get(f"/assessments?session_id={sid}").json()
    assert len(rows) == 1


def test_suicide_item_raises_crisis_alert(client, sid):
    r = _submit(client, sid, answers=[0] * 8 + [1])
    body = r.json()
    assert body["assessment"]["suicide_flag"] is True
    assert body["crisis_alert"] is True
    assert "112" in body["crisis_message"]


def test_authenticated_submit_attaches_user(client, auth, sid):
    assert _submit(client, sid, headers=auth["headers"]).status_code == 200

    from api import db as _db
    from api.db.models import Assessment
    with _db.get_sessionmaker()() as s:
        row = s.query(Assessment).one()
        assert row.user_id == auth["uid"], "ölçüm hesaba bağlanmadı"


def test_history_survives_new_session(client, auth):
    """Asıl hata: her yeni sohbette grafik sıfırlanıyordu."""
    from api.session import get_store
    store = get_store()

    ilk = store.new_session()
    _submit(client, ilk, answers=AGIR, headers=auth["headers"])

    ikinci = store.new_session()
    _submit(client, ikinci, answers=HAFIF, headers=auth["headers"])

    # session_id vermeden, yalnızca hesapla
    rows = client.get("/assessments", headers=auth["headers"]).json()
    assert [r["total_score"] for r in rows] == [24, 8]

    son = client.get("/assessments/latest", headers=auth["headers"]).json()
    assert son["total_score"] == 8


def test_authenticated_scope_ignores_session_id(client, auth):
    from api.session import get_store
    store = get_store()
    ilk = store.new_session()
    _submit(client, ilk, headers=auth["headers"])

    baska = store.new_session()
    rows = client.get(f"/assessments?session_id={baska}", headers=auth["headers"]).json()
    assert len(rows) == 1, "hesap kapsamı oturum kimliğine göre daralmamalı"


def test_anonymous_cannot_read_account_records(client, auth, sid):
    """Oturum kimliği ele geçse bile hesaba bağlı kayıt sızmamalı."""
    _submit(client, sid, headers=auth["headers"])

    assert client.get(f"/assessments?session_id={sid}").json() == []
    assert client.get(f"/assessments/latest?session_id={sid}").json() is None


def test_users_do_not_see_each_other(client, auth, sid):
    _submit(client, sid, headers=auth["headers"])

    other_email = f"o{uuid.uuid4().hex[:8]}@test.com"
    _make_user(other_email)
    other = _login(client, other_email)
    assert client.get("/assessments", headers=other).json() == []


def test_anonymous_list_requires_session_id(client):
    assert client.get("/assessments").status_code == 400
    assert client.get("/assessments?session_id=degil").status_code == 400


def test_bad_answers_rejected(client, sid):
    assert _submit(client, sid, answers=[1] * 8).status_code == 422
    assert _submit(client, sid, answers=[9] * 9).status_code == 422
    assert _submit(client, sid, kind="yok").status_code == 422


def test_gad7_scoring(client, sid):
    r = _submit(client, sid, answers=[2] * 7, kind="gad7")
    assert r.json()["assessment"]["total_score"] == 14
    assert r.json()["assessment"]["severity"] == "moderate"


def test_first_assessment_milestone(client, auth, sid):
    _submit(client, sid, headers=auth["headers"])
    body = client.get("/auth/me/insights", headers=auth["headers"]).json()
    tas = [m for m in body["milestones"] if m["kind"] == "first_assessment"]
    assert tas and tas[0]["detail"] == "PHQ9"


def test_authenticated_needs_no_session(client, auth):
    """Girişli kullanıcı hiç konuşmadan ölçüm yapabilmeli."""
    r = client.post(
        "/assessments",
        json={"kind": "phq9", "answers": HAFIF},
        headers=auth["headers"],
    )
    assert r.status_code == 200, r.text
    assert client.get("/assessments", headers=auth["headers"]).json()[0]["total_score"] == 8


def test_no_empty_session_is_created(client, auth):
    client.post("/assessments", json={"kind": "phq9", "answers": HAFIF}, headers=auth["headers"])

    from api import db as _db
    from api.db.models import ChatSession
    with _db.get_sessionmaker()() as s:
        assert s.query(ChatSession).count() == 0, "ölçüm için boş sohbet açılmış"

    # Sohbetlerim listesinde de hiçbir şey görünmemeli.
    assert client.get("/auth/sessions", headers=auth["headers"]).json()["total"] == 0


def test_anonymous_still_requires_session(client):
    r = client.post("/assessments", json={"kind": "phq9", "answers": HAFIF})
    assert r.status_code == 400


def test_assessment_from_chat_keeps_session_link(client, auth, sid):
    """Sohbetin içinden yapılan ölçüm oturuma bağlı kalmalı."""
    _submit(client, sid, headers=auth["headers"])

    from api import db as _db
    from api.db.models import Assessment
    with _db.get_sessionmaker()() as s:
        assert str(s.query(Assessment).one().session_id) == sid
