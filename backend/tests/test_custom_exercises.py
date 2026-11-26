from app.config import get_settings


def names(client, headers):
    return [e["name"] for e in client.get("/api/exercises", headers=headers).json()]


def create(client, headers, name="Hammer Strength Row", equipment="Machine", muscle="Back"):
    return client.post(
        "/api/exercises",
        json={"name": name, "equipment": equipment, "muscle_group": muscle},
        headers=headers,
    )


def test_custom_exercise_is_personal(client, signed_in):
    alice = signed_in("alice@example.com")
    bob = signed_in("bob@example.com")
    res = create(client, alice, name="  Hammer   Strength Row ")
    assert res.status_code == 201
    ex = res.json()
    assert ex["name"] == "Hammer Strength Row"  # whitespace tidied
    assert ex["custom"] is True and ex["retired"] is False

    assert "Hammer Strength Row" in names(client, alice)
    assert "Hammer Strength Row" not in names(client, bob)
    # Bob can't open, log to, edit or delete it.
    assert client.get(f"/api/exercises/{ex['id']}", headers=bob).status_code == 404
    log = {"weight": 100, "reps": 10, "sets": 3}
    assert client.post(f"/api/exercises/{ex['id']}/logs", json=log, headers=bob).status_code == 404
    assert client.get(f"/api/exercises/{ex['id']}/logs", headers=bob).status_code == 404
    assert (
        client.patch(f"/api/exercises/{ex['id']}", json={"name": "x"}, headers=bob).status_code
        == 404
    )
    assert client.delete(f"/api/exercises/{ex['id']}", headers=bob).status_code == 404

    # Alice can log to it, and it shows in her Recent.
    assert (
        client.post(f"/api/exercises/{ex['id']}/logs", json=log, headers=alice).status_code == 201
    )
    recent = client.get("/api/exercises/recent", headers=alice).json()
    assert recent[0]["exercise"]["custom"] is True


def test_names_unique_per_user_but_may_match_catalog(client, signed_in):
    alice = signed_in("alice@example.com")
    bob = signed_in("bob@example.com")
    assert create(client, alice).status_code == 201
    assert create(client, alice, name="hammer strength row").status_code == 409
    assert create(client, bob).status_code == 201  # someone else's is fine
    assert (
        create(client, alice, name="Bench Press", equipment="Barbell", muscle="Chest").status_code
        == 201
    )


def test_validation(client, signed_in):
    headers = signed_in()
    assert create(client, headers, name="   ").status_code == 422
    assert create(client, headers, name="x" * 81).status_code == 422
    assert create(client, headers, equipment="Spaceship").status_code == 422
    assert create(client, headers, muscle="Elbows").status_code == 422


def test_edit_custom_but_not_catalog(client, signed_in):
    headers = signed_in()
    ex = create(client, headers).json()
    other = create(client, headers, name="Belt Squat").json()
    res = client.patch(
        f"/api/exercises/{ex['id']}",
        json={"name": "Iso Row", "muscle_group": "Back"},
        headers=headers,
    )
    assert res.status_code == 200 and res.json()["name"] == "Iso Row"
    assert (
        client.patch(
            f"/api/exercises/{ex['id']}", json={"name": "belt squat"}, headers=headers
        ).status_code
        == 409
    )
    assert (
        client.patch(f"/api/exercises/{ex['id']}", json={"name": None}, headers=headers).status_code
        == 422
    )
    assert other["id"]

    bench = next(
        e
        for e in client.get("/api/exercises", headers=headers).json()
        if e["name"] == "Bench Press"
    )
    assert bench["custom"] is False
    assert (
        client.patch(
            f"/api/exercises/{bench['id']}", json={"name": "Mine"}, headers=headers
        ).status_code
        == 404
    )
    assert client.delete(f"/api/exercises/{bench['id']}", headers=headers).status_code == 404


def test_delete_custom_removes_its_logs(client, signed_in):
    headers = signed_in()
    ex = create(client, headers).json()
    client.post(
        f"/api/exercises/{ex['id']}/logs",
        json={"weight": 50, "reps": 5, "sets": 5},
        headers=headers,
    )
    assert client.delete(f"/api/exercises/{ex['id']}", headers=headers).status_code == 204
    assert "Hammer Strength Row" not in names(client, headers)
    assert client.get("/api/exercises/recent", headers=headers).json() == []
    assert client.get("/api/stats", headers=headers).json()["entries"] == 0


def test_limit_when_set(client, signed_in, monkeypatch):
    monkeypatch.setattr(get_settings(), "custom_exercise_limit", 2)
    headers = signed_in()
    assert create(client, headers, name="One").status_code == 201
    assert create(client, headers, name="Two").status_code == 201
    res = create(client, headers, name="Three")
    assert res.status_code == 403
    assert "2 custom exercises" in res.json()["detail"]


def test_unlimited_until_billing(client, signed_in):
    assert get_settings().custom_exercise_limit is None
    headers = signed_in()
    for i in range(7):
        assert create(client, headers, name=f"Lift {i}").status_code == 201
