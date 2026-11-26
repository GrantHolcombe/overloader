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
