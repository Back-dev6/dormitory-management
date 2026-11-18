import os

from app.core.config import settings
from tests.helpers import A101, PNG, approve_into


def send(client, who_headers, files=None, title="Hỏng vòi nước"):
    return client.post("/api/incidents", headers=who_headers,
                       data={"title": title, "description": "Vòi nước nhà tắm bị rò"}, files=files)


def stored_files() -> int:
    folder = os.path.join(settings.STORAGE_DIR, "incidents")
    return len(os.listdir(folder)) if os.path.isdir(folder) else 0


def test_student_without_contract_cannot_report(client, auth):
    assert send(client, auth("m2")).status_code == 409


def test_upload_and_view_image_with_permission_checks(client, auth):
    approve_into(client, auth, "m1", A101)
    r = send(client, auth("m1"), files={"image": ("a.png", PNG, "image/png")})
    assert r.status_code == 201 and r.json()["image_url"]
    url = r.json()["image_url"]
    owner = client.get(url, headers=auth("m1"))
    assert owner.status_code == 200 and owner.content == PNG
    assert owner.headers["cache-control"] == "no-store"
    assert client.get(url, headers=auth("m2")).status_code == 403   # sinh viên khác
    assert client.get(url, headers=auth("mgr")).status_code == 200  # cán bộ
    assert client.get(url).status_code == 401


def test_fake_image_is_rejected_and_nothing_is_stored(client, auth):
    approve_into(client, auth, "m1", A101)
    before = stored_files()
    r = send(client, auth("m1"), files={"image": ("x.png", b"MZ\x90\x00 khong phai anh", "image/png")})
    assert r.status_code == 422
    assert stored_files() == before


def test_oversized_image_is_rejected(client, auth):
    approve_into(client, auth, "m1", A101)
    big = PNG + b"\0" * (settings.MAX_UPLOAD_MB * 1024 * 1024 + 10)
    assert send(client, auth("m1"), files={"image": ("big.png", big, "image/png")}).status_code == 413


def test_status_only_moves_forward(client, auth):
    approve_into(client, auth, "m1", A101)
    inc_id = send(client, auth("m1")).json()["id"]
    url = f"/api/incidents/{inc_id}/status"
    assert client.patch(url, json={"status": "IN_PROGRESS"}, headers=auth("m1")).status_code == 403
    assert client.patch(url, json={"status": "IN_PROGRESS"}, headers=auth("mgr")).status_code == 200
    assert client.patch(url, json={"status": "RESOLVED"}, headers=auth("mgr")).status_code == 200
    assert client.patch(url, json={"status": "IN_PROGRESS"}, headers=auth("mgr")).status_code == 409
