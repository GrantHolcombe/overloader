from urllib.parse import urlencode


def exercise_id(client, headers, name):
    rows = client.get("/api/exercises", headers=headers).json()
    return next(e["id"] for e in rows if e["name"] == name)


def log(client, headers, exercise, when, weight=100):
    body = {"weight": weight, "reps": 5, "sets": 3, "performed_at": when}
    res = client.post(f"/api/exercises/{exercise}/logs", json=body, headers=headers)
    assert res.status_code == 201, res.text


def day(client, headers, start, end):
    return client.get("/api/logs?" + urlencode({"start": start, "end": end}), headers=headers)


def test_entries_for_a_local_day(client, signed_in):
    headers = signed_in()
    bench = exercise_id(client, headers, "Bench Press")
    squat = exercise_id(client, headers, "Back Squat")
    # Friday Nov 20 in UTC-8 runs from 08:00Z Nov 20 to 08:00Z Nov 21.
    log(client, headers, bench, "2026-11-20T07:59:00Z")  # Thursday evening locally
    log(client, headers, squat, "2026-11-20T18:00:00Z", weight=225)
    log(client, headers, bench, "2026-11-21T03:30:00Z", weight=135)  # Friday 7:30 pm locally
    log(client, headers, bench, "2026-11-21T08:00:00Z")  # Saturday midnight: excluded

    res = day(client, headers, "2026-11-20T00:00:00-08:00", "2026-11-21T00:00:00-08:00")
    assert res.status_code == 200
    rows = res.json()
    assert [(r["exercise"]["name"], r["weight"]) for r in rows] == [
        ("Back Squat", 225),
        ("Bench Press", 135),
    ]  # oldest first, each with its exercise


def test_only_your_entries(client, signed_in):
    alice = signed_in("alice@example.com")
    bob = signed_in("bob@example.com")
    log(client, alice, exercise_id(client, alice, "Bench Press"), "2026-11-20T18:00:00Z")
    assert day(client, bob, "2026-11-20T00:00:00Z", "2026-11-21T00:00:00Z").json() == []


def test_range_validation(client, signed_in):
    headers = signed_in()
    assert day(client, headers, "2026-11-21T00:00:00Z", "2026-11-20T00:00:00Z").status_code == 422
    assert day(client, headers, "2026-01-01T00:00:00Z", "2026-12-01T00:00:00Z").status_code == 422
    assert day(client, headers, "2026-11-20T00:00:00", "2026-11-21T00:00:00").status_code == 422
    assert client.get("/api/logs", headers=headers).status_code == 422
