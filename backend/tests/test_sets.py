"""Per-set entries: each set with its own weight and reps."""


def bench_url(client, headers):
    rows = client.get("/api/exercises", headers=headers).json()
    bench = next(e["id"] for e in rows if e["name"] == "Bench Press")
    return f"/api/exercises/{bench}/logs"


PYRAMID = [
    {"weight": 135, "reps": 10},
    {"weight": 155, "reps": 6},
    {"weight": 155, "reps": 5},
    {"weight": 145, "reps": 8},
]


def test_log_per_set_and_summary(client, signed_in):
    headers = signed_in()
    url = bench_url(client, headers)
    res = client.post(url, json={"set_details": PYRAMID}, headers=headers)
    assert res.status_code == 201, res.text
    entry = res.json()
    # Summary: the heaviest set (the first of two 155s) and the number of sets.
    assert (entry["weight"], entry["reps"], entry["sets"]) == (155, 6, 4)
    assert entry["set_details"] == PYRAMID  # in order
    assert entry["unit"] == "lb"

    # It comes back the same everywhere entries are read.
    assert client.get(url, headers=headers).json()[0]["set_details"] == PYRAMID
    recent = client.get("/api/exercises/recent", headers=headers).json()
    assert recent[0]["last"]["set_details"] == PYRAMID


def test_quick_entries_have_no_set_details(client, signed_in):
    headers = signed_in()
    url = bench_url(client, headers)
    entry = client.post(url, json={"weight": 135, "reps": 8, "sets": 3}, headers=headers).json()
    assert entry["set_details"] == []


def test_validation(client, signed_in):
    headers = signed_in()
    url = bench_url(client, headers)
    bad = [
        {},  # nothing
        {"weight": 135, "reps": 8},  # quick but no sets
        {"set_details": []},
        {"set_details": [{"weight": 135, "reps": 0}]},
        {"set_details": [{"weight": -1, "reps": 5}]},
        {"set_details": [{"weight": 100, "reps": 5}] * 101},
        {"weight": 135, "reps": 8, "sets": 3, "set_details": PYRAMID},  # both
    ]
    for body in bad:
        assert client.post(url, json=body, headers=headers).status_code == 422, body


def test_edit_sets_then_back_to_quick(client, signed_in):
    headers = signed_in()
    url = bench_url(client, headers)
    entry = client.post(url, json={"set_details": PYRAMID}, headers=headers).json()

    # Replace the sets: the summary follows.
    sets = [{"weight": 165, "reps": 3}, {"weight": 135, "reps": 12}]
    res = client.patch(f"/api/logs/{entry['id']}", json={"set_details": sets}, headers=headers)
    assert res.status_code == 200, res.text
    edited = res.json()
    assert edited["set_details"] == sets
    assert (edited["weight"], edited["reps"], edited["sets"]) == (165, 3, 2)

    # Moving the date alone keeps the sets.
    moved = client.patch(
        f"/api/logs/{entry['id']}", json={"performed_at": "2026-11-20T18:00:00Z"}, headers=headers
    ).json()
    assert moved["set_details"] == sets

    # Quick fields turn it back into a quick entry.
    quick = client.patch(
        f"/api/logs/{entry['id']}", json={"weight": 140, "reps": 8, "sets": 3}, headers=headers
    ).json()
    assert quick["set_details"] == []
    assert (quick["weight"], quick["reps"], quick["sets"]) == (140, 8, 3)

    # And a quick entry can become per-set.
    again = client.patch(
        f"/api/logs/{entry['id']}", json={"set_details": PYRAMID}, headers=headers
    ).json()
    assert again["set_details"] == PYRAMID

    both = {"weight": 1, "set_details": PYRAMID}
    assert client.patch(f"/api/logs/{entry['id']}", json=both, headers=headers).status_code == 422


def test_deleting_an_entry_deletes_its_sets(client, signed_in):
    headers = signed_in()
    url = bench_url(client, headers)
    entry = client.post(url, json={"set_details": PYRAMID}, headers=headers).json()
    assert client.delete(f"/api/logs/{entry['id']}", headers=headers).status_code == 204
    from sqlalchemy import text

    from app.db import get_engine

    with get_engine().connect() as conn:
        left = conn.execute(
            text("SELECT count(*) FROM log_set WHERE log_entry_id = :id"), {"id": entry["id"]}
        ).scalar()
    assert left == 0
