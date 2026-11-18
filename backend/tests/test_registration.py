from tests.helpers import A101, A102, B101, approve_into


def register(client, auth, who, room):
    return client.post("/api/registrations", json={"room_id": room}, headers=auth(who))


def occupied(client, room):
    return client.get(f"/api/rooms/{room}").json()["occupied_beds"]


def test_full_flow_register_approve_creates_contract(client, auth):
    r = register(client, auth, "m1", A101)
    assert r.status_code == 201 and r.json()["status"] == "PENDING"
    assert occupied(client, A101) == 0  # đơn chờ KHÔNG giữ chỗ
    reg_id = r.json()["id"]
    r = client.post(f"/api/registrations/{reg_id}/approve", headers=auth("mgr"))
    assert r.status_code == 200
    assert r.json()["registration"]["status"] == "APPROVED" and r.json()["contract"]["status"] == "ACTIVE"
    assert occupied(client, A101) == 1
    assert len(client.get("/api/contracts/me", headers=auth("m1")).json()) == 1


def test_gender_must_match_building(client, auth):
    assert register(client, auth, "f1", A101).status_code == 409
    assert register(client, auth, "m1", B101).status_code == 409


def test_one_pending_registration_per_student(client, auth):
    assert register(client, auth, "m1", A101).status_code == 201
    assert register(client, auth, "m1", A102).status_code == 409


def test_cannot_approve_twice(client, auth):
    _, reg_id = approve_into(client, auth, "m1", A101)
    assert client.post(f"/api/registrations/{reg_id}/approve", headers=auth("mgr")).status_code == 409
    assert occupied(client, A101) == 1


def test_student_cannot_approve(client, auth):
    reg_id = register(client, auth, "m1", A101).json()["id"]
    assert client.post(f"/api/registrations/{reg_id}/approve", headers=auth("m2")).status_code == 403


def test_reject_needs_reason_and_keeps_room_free(client, auth):
    reg_id = register(client, auth, "m1", A101).json()["id"]
    assert client.post(f"/api/registrations/{reg_id}/reject", json={}, headers=auth("mgr")).status_code == 422
    r = client.post(f"/api/registrations/{reg_id}/reject", json={"reason": "Hồ sơ chưa đủ"}, headers=auth("mgr"))
    assert r.status_code == 200 and r.json()["status"] == "REJECTED"
    assert occupied(client, A101) == 0


def test_student_can_cancel_own_pending_registration(client, auth):
    reg_id = register(client, auth, "m1", A101).json()["id"]
    assert client.post(f"/api/registrations/{reg_id}/cancel", headers=auth("m2")).status_code == 403
    assert client.post(f"/api/registrations/{reg_id}/cancel", headers=auth("m1")).status_code == 200
    assert register(client, auth, "m1", A101).status_code == 201  # hủy xong gửi lại được


def test_full_room_refuses_new_registrations(client, auth):
    approve_into(client, auth, "m1", A102)  # A102 chỉ có 1 giường
    r = register(client, auth, "m2", A102)
    assert r.status_code == 409 and "hết chỗ" in r.json()["detail"]


def test_ending_contract_frees_the_bed(client, auth):
    contract_id, _ = approve_into(client, auth, "m1", A101)
    assert occupied(client, A101) == 1
    assert client.post(f"/api/contracts/{contract_id}/end", headers=auth("mgr")).status_code == 200
    assert occupied(client, A101) == 0
    assert client.post(f"/api/contracts/{contract_id}/end", headers=auth("mgr")).status_code == 409
