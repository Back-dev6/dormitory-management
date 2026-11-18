from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from tests.helpers import EMAILS, PASSWORD


def login(client, email=EMAILS["m1"], password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_success_returns_tokens_without_hash(client):
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == settings.ACCESS_TOKEN_MINUTES * 60
    assert body["user"]["role"] == "STUDENT"
    assert "password_hash" not in body["user"]


def test_wrong_password_and_unknown_email_give_same_message(client):
    a = login(client, password="Sai12345678")
    b = login(client, email="khongco@test.vn")
    assert a.status_code == b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"]  # không lộ email nào có tài khoản


def test_invalid_tokens_are_rejected(client, auth):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer rac.rac.rac"}).status_code == 401
    good = auth("m1")["Authorization"].split()[1]
    tampered = good[:-4] + ("AAAA" if not good.endswith("AAAA") else "BBBB")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401
    expired = jwt.encode({"sub": "1", "type": "access", "exp": datetime.now(timezone.utc) - timedelta(seconds=5)},
                         settings.JWT_SECRET, algorithm="HS256")
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
    refresh = login(client).json()["refresh_token"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {refresh}"}).status_code == 401


def test_refresh_rotates_and_reuse_revokes_everything(client):
    first = login(client).json()
    second = client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert second.status_code == 200
    new_refresh = second.json()["refresh_token"]
    assert new_refresh != first["refresh_token"]
    # dùng lại token cũ => 401 và token mới cũng bị thu hồi
    assert client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": new_refresh}).status_code == 401


def test_logout_revokes_refresh_token(client):
    t = login(client).json()
    assert client.post("/api/auth/logout", json={"refresh_token": t["refresh_token"]}).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_register_cannot_escalate_role(client):
    body = {"email": "moi@example.com", "password": "Matkhau123", "full_name": "Sinh Vien Moi",
            "student_code": "SVM001", "gender": "MALE", "role": "ADMIN"}
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201 and r.json()["role"] == "STUDENT"
    assert client.post("/api/auth/register", json=body).status_code == 409  # trùng email


def test_weak_passwords_are_rejected(client):
    base = {"email": "yeu@example.com", "full_name": "Mat Khau Yeu", "student_code": "YEU01", "gender": "MALE"}
    for weak in ("ngan1", "khongcoso", "12345678"):
        assert client.post("/api/auth/register", json={**base, "password": weak}).status_code == 422


def test_brute_force_lockout_after_five_failures(client):
    for _ in range(5):
        assert login(client, password="Sai12345678").status_code == 401
    r = login(client)  # đúng mật khẩu nhưng đang bị khóa
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0
    assert login(client, email=EMAILS["m2"]).status_code == 200  # tài khoản khác không bị ảnh hưởng


def test_change_password_revokes_sessions(client, auth):
    t = login(client).json()
    h = {"Authorization": f"Bearer {t['access_token']}"}
    assert client.post("/api/auth/change-password", headers=h,
                       json={"old_password": "Sai12345678", "new_password": "Moi123456"}).status_code == 400
    assert client.post("/api/auth/change-password", headers=h,
                       json={"old_password": PASSWORD, "new_password": "Moi123456"}).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401
    assert login(client, password="Moi123456").status_code == 200
