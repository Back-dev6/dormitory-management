import pytest

from app.core.config import settings
from tests.helpers import A101, approve_into

ALLOWED_ORIGIN = settings.cors_origin_list[0]


def test_security_headers_are_present(client):
    h = client.get("/api/health").headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert "default-src 'none'" in h["content-security-policy"]
    assert client.post("/api/auth/login", json={"email": "a@b.c", "password": "x"}).headers["cache-control"] == "no-store"


def test_cors_allows_only_listed_origins(client):
    ok = client.options("/api/rooms", headers={"Origin": ALLOWED_ORIGIN, "Access-Control-Request-Method": "GET"})
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    bad = client.options("/api/rooms", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert bad.status_code == 400 and "access-control-allow-origin" not in bad.headers


@pytest.mark.parametrize("who,path,expected", [
    (None, "/api/invoices/me", 401),
    ("m1", "/api/users", 403),
    ("mgr", "/api/users", 403),
    ("admin", "/api/users", 200),
    ("m1", "/api/statistics/occupancy", 403),
    ("mgr", "/api/statistics/occupancy", 200),
    ("mgr", "/api/invoices/me", 403),
])
def test_role_matrix(client, auth, who, path, expected):
    headers = auth(who) if who else {}
    assert client.get(path, headers=headers).status_code == expected


def test_disabling_account_takes_effect_immediately(client, auth):
    victim = auth("m1")
    assert client.get("/api/auth/me", headers=victim).status_code == 200
    uid = client.get("/api/auth/me", headers=victim).json()["id"]
    assert client.put(f"/api/users/{uid}", json={"is_active": False}, headers=auth("admin")).status_code == 200
    assert client.get("/api/auth/me", headers=victim).status_code == 401
    admin_id = client.get("/api/auth/me", headers=auth("admin")).json()["id"]
    assert client.put(f"/api/users/{admin_id}", json={"is_active": False}, headers=auth("admin")).status_code == 409


def test_occupancy_statistics_match_data(client, auth):
    approve_into(client, auth, "m1", A101)
    rep = client.get("/api/statistics/occupancy", headers=auth("mgr")).json()
    a, b = rep["buildings"]
    assert (a["total_beds"], a["occupied_beds"], a["occupancy_rate"]) == (3, 1, 33.33)
    assert (b["total_beds"], b["occupied_beds"], b["occupancy_rate"]) == (4, 0, 0)
    assert (rep["total_beds"], rep["occupied_beds"], rep["occupancy_rate"]) == (7, 1, 14.29)
