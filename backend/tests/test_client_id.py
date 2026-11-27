"""Retries with the same client_id don't log twice (the app's offline queue relies on this)."""

import uuid


def bench_url(client, headers):
    rows = client.get("/api/exercises", headers=headers).json()
    bench = next(e["id"] for e in rows if e["name"] == "Bench Press")
    return f"/api/exercises/{bench}/logs"


def test_same_client_id_returns_the_saved_entry(client, signed_in):
    headers = signed_in()
    url = bench_url(client, headers)
    body = {"weight": 135, "reps": 8, "sets": 3, "client_id": str(uuid.uuid4())}

    first = client.post(url, json=body, headers=headers)
    again = client.post(url, json=body, headers=headers)

    assert first.status_code == 201
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
    assert len(client.get(url, headers=headers).json()) == 1


def test_per_set_retry_keeps_its_sets(client, signed_in):
    headers = signed_in()
    url = bench_url(client, headers)
    body = {"set_details": [{"weight": 135, "reps": 8}, {"weight": 145, "reps": 6}]}
    body["client_id"] = str(uuid.uuid4())

    client.post(url, json=body, headers=headers)
    again = client.post(url, json=body, headers=headers).json()

    assert [s["weight"] for s in again["set_details"]] == [135, 145]
    assert len(client.get(url, headers=headers).json()) == 1


def test_different_client_ids_and_none_each_log(client, signed_in):
    headers = signed_in()
    url = bench_url(client, headers)
    for client_id in (str(uuid.uuid4()), str(uuid.uuid4()), None, None):
        body = {"weight": 100, "reps": 5, "sets": 5}
        if client_id:
            body["client_id"] = client_id
        assert client.post(url, json=body, headers=headers).status_code == 201
    assert len(client.get(url, headers=headers).json()) == 4


def test_client_ids_are_per_user(client, signed_in):
    alice = signed_in("alice@example.com")
    bob = signed_in("bob@example.com")
    url = bench_url(client, alice)
    body = {"weight": 100, "reps": 5, "sets": 5, "client_id": str(uuid.uuid4())}

    a = client.post(url, json=body, headers=alice)
    b = client.post(url, json=body, headers=bob)

    # Bob gets his own entry, never Alice's.
    assert a.status_code == b.status_code == 201
    assert a.json()["id"] != b.json()["id"]


def test_bad_client_id_is_rejected(client, signed_in):
    headers = signed_in()
    url = bench_url(client, headers)
    body = {"weight": 100, "reps": 5, "sets": 5, "client_id": "not-a-uuid"}
    assert client.post(url, json=body, headers=headers).status_code == 422
