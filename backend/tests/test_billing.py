import io

from openpyxl import load_workbook

from tests.helpers import A101, A102, approve_into, current_ym, next_ym, post_reading, prev_ym


def test_reading_generates_invoice_with_correct_amounts(client, auth):
    approve_into(client, auth, "m1", A101)  # A101: 300.000 đ/giường, 1 người ở
    r = post_reading(client, auth, A101, current_ym(), electric_new=120, water_new=8)
    assert r.status_code == 201
    inv = r.json()["invoice"]
    assert (inv["electric_usage"], inv["water_usage"]) == (120, 8)
    assert float(inv["electric_amount"]) == 120 * 3500
    assert float(inv["water_amount"]) == 8 * 15000
    assert float(inv["room_fee"]) == 300000
    assert float(inv["total"]) == 420000 + 120000 + 300000
    assert inv["status"] == "UNPAID"


def test_old_readings_come_from_previous_month(client, auth):
    assert post_reading(client, auth, A101, prev_ym(), 100, 5).status_code == 201
    r = post_reading(client, auth, A101, current_ym(), 220, 13)
    assert r.status_code == 201
    rd = r.json()["reading"]
    assert (rd["electric_old"], rd["water_old"]) == (100, 5)
    assert r.json()["invoice"]["electric_usage"] == 120


def test_invalid_readings_are_rejected(client, auth):
    assert post_reading(client, auth, A101, current_ym(), 100, 5).status_code == 201
    assert post_reading(client, auth, A101, current_ym(), 200, 9).status_code == 409   # trùng tháng
    assert post_reading(client, auth, A101, prev_ym(), 50, 2).status_code == 409       # chèn tháng cũ
    assert post_reading(client, auth, A102, current_ym(), 10, 1, electric_old=50).status_code == 422  # mới < cũ
    assert post_reading(client, auth, A102, next_ym(), 10, 1).status_code == 422       # tháng tương lai
    assert post_reading(client, auth, 999, current_ym(), 10, 1).status_code == 404


def test_student_sees_only_own_room_invoices(client, auth):
    approve_into(client, auth, "m1", A101)
    approve_into(client, auth, "m2", A102)
    id1 = post_reading(client, auth, A101, current_ym(), 10, 1).json()["invoice"]["id"]
    id2 = post_reading(client, auth, A102, current_ym(), 10, 1).json()["invoice"]["id"]
    mine = client.get("/api/invoices/me", headers=auth("m1")).json()
    assert [i["id"] for i in mine] == [id1]
    assert client.get(f"/api/invoices/{id1}", headers=auth("m1")).status_code == 200
    assert client.get(f"/api/invoices/{id2}", headers=auth("m1")).status_code == 403
    assert client.get("/api/invoices", headers=auth("m1")).status_code == 403


def test_pay_invoice_once(client, auth):
    approve_into(client, auth, "m1", A101)
    inv_id = post_reading(client, auth, A101, current_ym(), 10, 1).json()["invoice"]["id"]
    assert client.post(f"/api/invoices/{inv_id}/pay", headers=auth("m1")).status_code == 403
    r = client.post(f"/api/invoices/{inv_id}/pay", headers=auth("mgr"))
    assert r.status_code == 200 and r.json()["status"] == "PAID" and r.json()["paid_at"]
    assert client.post(f"/api/invoices/{inv_id}/pay", headers=auth("mgr")).status_code == 409


def test_excel_export_contains_invoices_and_total_formula(client, auth):
    approve_into(client, auth, "m1", A101)
    post_reading(client, auth, A101, current_ym(), 120, 8)
    r = client.get("/api/invoices/export", headers=auth("mgr"))
    assert r.status_code == 200 and "spreadsheetml" in r.headers["content-type"]
    ws = load_workbook(io.BytesIO(r.content)).active
    assert ws.cell(row=1, column=1).value == "Mã HĐ"
    assert ws.cell(row=2, column=3).value == "A101"
    assert ws.cell(row=2, column=14).value == 840000
    assert str(ws.cell(row=3, column=14).value).startswith("=SUM(")
    assert client.get("/api/invoices/export", headers=auth("m1")).status_code == 403
