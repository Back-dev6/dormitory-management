from tests.helpers import A101, approve_into


def names(r):
    return sorted(i["room_number"] for i in r.json()["items"])


def test_public_listing_and_filters(client):
    assert names(client.get("/api/rooms")) == ["A101", "A102", "B101"]
    assert names(client.get("/api/rooms", params={"gender": "MALE"})) == ["A101", "A102"]
    assert names(client.get("/api/rooms", params={"max_price": 300000})) == ["A101"]
    r = client.get("/api/rooms", params={"page": 2, "page_size": 2})
    assert r.json()["total"] == 3 and len(r.json()["items"]) == 1


def test_available_only_hides_full_rooms(client, auth):
    approve_into(client, auth, "m1", 2)  # A102 chỉ có 1 giường -> đầy
    assert "A102" not in names(client.get("/api/rooms", params={"available_only": True}))
    assert "A102" in names(client.get("/api/rooms"))


def test_invalid_price_range_is_422(client):
    assert client.get("/api/rooms", params={"min_price": 500, "max_price": 100}).status_code == 422


def test_only_staff_can_create_rooms(client, auth):
    body = {"building_id": 1, "room_number": "A201", "floor": 2, "max_beds": 4, "price_per_bed": "280000"}
    assert client.post("/api/rooms", json=body, headers=auth("m1")).status_code == 403
    assert client.post("/api/rooms", json=body).status_code == 401
    assert client.post("/api/rooms", json=body, headers=auth("mgr")).status_code == 201
    assert client.post("/api/rooms", json=body, headers=auth("mgr")).status_code == 409  # trùng số phòng


def test_cannot_reduce_beds_below_occupancy(client, auth):
    approve_into(client, auth, "m1", A101)
    approve_into(client, auth, "m2", A101)
    r = client.put(f"/api/rooms/{A101}", json={"max_beds": 1}, headers=auth("mgr"))
    assert r.status_code == 409
