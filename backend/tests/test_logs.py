def exercise_id(client, headers, name):
    rows = client.get("/api/exercises", headers=headers).json()
    return next(e["id"] for e in rows if e["name"] == name)


def test_catalog_is_seeded(client, signed_in):
    headers = signed_in()
    rows = client.get("/api/exercises", headers=headers).json()
    names = {e["name"] for e in rows}
    assert {"Bench Press", "Back Squat", "Lat Pulldown", "Leg Press"} <= names
    assert len(rows) > 50


def test_log_and_read_back(client, signed_in):
    headers = signed_in()
    bench = exercise_id(client, headers, "Bench Press")
    url = f"/api/exercises/{bench}/logs"

    first = client.post(url, json={"weight": 135, "reps": 8, "sets": 3}, headers=headers)
    assert first.status_code == 201
    assert first.json()["unit"] == "lb"
    client.post(url, json={"weight": "140.5", "reps": 6, "sets": 3}, headers=headers)

    logs = client.get(url, headers=headers).json()
    assert [entry["weight"] for entry in logs] == [140.5, 135]  # newest first

    recent = client.get("/api/exercises/recent", headers=headers).json()
    assert recent[0]["exercise"]["name"] == "Bench Press"
    assert recent[0]["last"]["weight"] == 140.5


def test_recent_has_one_row_per_exercise(client, signed_in):
    headers = signed_in()
    bench = exercise_id(client, headers, "Bench Press")
    squat = exercise_id(client, headers, "Back Squat")
    for ex in (bench, squat, bench):
        client.post(
            f"/api/exercises/{ex}/logs", json={"weight": 100, "reps": 5, "sets": 5}, headers=headers
        )
    recent = client.get("/api/exercises/recent", headers=headers).json()
    assert [r["exercise"]["name"] for r in recent] == ["Bench Press", "Back Squat"]


def test_logs_are_private(client, signed_in):
    alice = signed_in("alice@example.com")
    bob = signed_in("bob@example.com")
    bench = exercise_id(client, alice, "Bench Press")
    entry = client.post(
        f"/api/exercises/{bench}/logs", json={"weight": 95, "reps": 10, "sets": 3}, headers=alice
    ).json()

    assert client.get(f"/api/exercises/{bench}/logs", headers=bob).json() == []
    assert client.delete(f"/api/logs/{entry['id']}", headers=bob).status_code == 404
    assert client.delete(f"/api/logs/{entry['id']}", headers=alice).status_code == 204
    assert client.get(f"/api/exercises/{bench}/logs", headers=alice).json() == []


def test_validation(client, signed_in):
    headers = signed_in()
    bench = exercise_id(client, headers, "Bench Press")
    url = f"/api/exercises/{bench}/logs"
    for bad in (
        {"weight": -5, "reps": 5, "sets": 3},
        {"weight": 100, "reps": 0, "sets": 3},
        {"weight": 100, "reps": 5, "sets": 0},
        {"weight": 100.123, "reps": 5, "sets": 3},
    ):
        assert client.post(url, json=bad, headers=headers).status_code == 422, bad
    assert (
        client.post(
            "/api/exercises/999999/logs", json={"weight": 1, "reps": 1, "sets": 1}, headers=headers
        ).status_code
        == 404
    )


def test_entry_keeps_its_unit(client, signed_in):
    headers = signed_in()
    bench = exercise_id(client, headers, "Bench Press")
    url = f"/api/exercises/{bench}/logs"
    client.post(url, json={"weight": 100, "reps": 5, "sets": 3}, headers=headers)
    client.patch("/api/me", json={"unit": "kg"}, headers=headers)
    client.post(url, json={"weight": 50, "reps": 5, "sets": 3}, headers=headers)
    assert [e["unit"] for e in client.get(url, headers=headers).json()] == ["kg", "lb"]


def test_log_a_past_date(client, signed_in):
    headers = signed_in()
    bench = exercise_id(client, headers, "Bench Press")
    url = f"/api/exercises/{bench}/logs"
    client.post(url, json={"weight": 135, "reps": 8, "sets": 3}, headers=headers)
    past = client.post(
        url,
        json={"weight": 125, "reps": 8, "sets": 3, "performed_at": "2026-11-01T12:00:00-08:00"},
        headers=headers,
    )
    assert past.status_code == 201
    assert past.json()["performed_at"].startswith("2026-11-01T20:00:00")
    # The older entry sorts after today's, so "last time" is still today's.
    assert [e["weight"] for e in client.get(url, headers=headers).json()] == [135, 125]


def test_rejects_future_and_naive_dates(client, signed_in):
    headers = signed_in()
    bench = exercise_id(client, headers, "Bench Press")
    url = f"/api/exercises/{bench}/logs"
    base = {"weight": 100, "reps": 5, "sets": 3}
    future = {**base, "performed_at": "2999-01-01T12:00:00Z"}
    naive = {**base, "performed_at": "2026-11-01T12:00:00"}
    assert client.post(url, json=future, headers=headers).status_code == 422
    assert client.post(url, json=naive, headers=headers).status_code == 422


def test_edit_entry(client, signed_in):
    headers = signed_in()
    bench = exercise_id(client, headers, "Bench Press")
    entry = client.post(
        f"/api/exercises/{bench}/logs", json={"weight": 315, "reps": 8, "sets": 3}, headers=headers
    ).json()

    # Fix a typo: only the fields sent change.
    res = client.patch(f"/api/logs/{entry['id']}", json={"weight": 135}, headers=headers)
    assert res.status_code == 200
    assert (res.json()["weight"], res.json()["reps"], res.json()["sets"]) == (135, 8, 3)

    moved = client.patch(
        f"/api/logs/{entry['id']}",
        json={"performed_at": "2026-11-20T18:00:00Z", "reps": 10},
        headers=headers,
    ).json()
    assert moved["performed_at"].startswith("2026-11-20T18:00:00")
    assert moved["reps"] == 10

    for bad in ({"reps": 0}, {"weight": None}, {"performed_at": "2999-01-01T00:00:00Z"}):
        assert (
            client.patch(f"/api/logs/{entry['id']}", json=bad, headers=headers).status_code == 422
        )


def test_cannot_edit_someone_elses_entry(client, signed_in):
    alice = signed_in("alice@example.com")
    bob = signed_in("bob@example.com")
    bench = exercise_id(client, alice, "Bench Press")
    entry = client.post(
        f"/api/exercises/{bench}/logs", json={"weight": 95, "reps": 10, "sets": 3}, headers=alice
    ).json()
    assert (
        client.patch(f"/api/logs/{entry['id']}", json={"weight": 1}, headers=bob).status_code == 404
    )
    assert client.get(f"/api/exercises/{bench}/logs", headers=alice).json()[0]["weight"] == 95
