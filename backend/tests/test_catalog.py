"""The catalog sync, run against copies of the CSVs in a temp folder."""

import csv

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import CatalogError, read_catalog, sync
from app.db import get_engine
from app.models import Exercise


def write_catalog(folder, rows, renames=()):
    with open(folder / "exercises.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "equipment", "muscle_group"])
        w.writerows(rows)
    with open(folder / "renames.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["old_name", "new_name"])
        w.writerows(renames)


@pytest.fixture
def real_rows():
    return read_catalog()[0]


def catalog_state():
    with Session(get_engine()) as db:
        rows = db.scalars(select(Exercise).where(Exercise.user_id.is_(None)))
        return {e.name: (e.equipment, e.muscle_group, e.retired_at is not None) for e in rows}


def run(folder, write=True):
    with Session(get_engine()) as db:
        return sync(db, write=write, directory=folder)


def test_real_csv_matches_database():
    with Session(get_engine()) as db:
        assert sync(db, write=False).empty()


def test_dry_run_writes_nothing(tmp_path, real_rows):
    write_catalog(tmp_path, [*real_rows, ("Zercher Squat", "Barbell", "Legs")])
    before = catalog_state()
    changes = run(tmp_path, write=False)
    assert changes.add == [("Zercher Squat", "Barbell", "Legs")]
    assert catalog_state() == before


def test_add_update_retire_and_restore(tmp_path, real_rows):
    rows = [r for r in real_rows if r[0] != "Good Morning"]
    rows = [(n, "Barbell", m) if n == "T-Bar Row" else (n, e, m) for n, e, m in rows]
    write_catalog(tmp_path, [*rows, ("Zercher Squat", "Barbell", "Legs")])
    changes = run(tmp_path)
    assert changes.add == [("Zercher Squat", "Barbell", "Legs")]
    assert changes.update == [("T-Bar Row", "Barbell", "Back")]
    assert changes.retire == ["Good Morning"]
    state = catalog_state()
    assert state["Zercher Squat"] == ("Barbell", "Legs", False)
    assert state["T-Bar Row"] == ("Barbell", "Back", False)
    assert state["Good Morning"][2] is True  # retired, not deleted

    # Putting it back restores it; running again changes nothing.
    write_catalog(tmp_path, [*real_rows, ("Zercher Squat", "Barbell", "Legs")])
    changes = run(tmp_path)
    assert changes.restore == ["Good Morning"]
    assert changes.update == [("T-Bar Row", "Machine", "Back")]
    assert run(tmp_path).empty()


def test_retired_exercise_keeps_history(tmp_path, real_rows, client, signed_in):
    headers = signed_in()
    good_morning = next(
        e
        for e in client.get("/api/exercises", headers=headers).json()
        if e["name"] == "Good Morning"
    )
    log = {"weight": 95, "reps": 10, "sets": 3}
    client.post(f"/api/exercises/{good_morning['id']}/logs", json=log, headers=headers)

    write_catalog(tmp_path, [r for r in real_rows if r[0] != "Good Morning"])
    run(tmp_path)

    listed = [e["name"] for e in client.get("/api/exercises", headers=headers).json()]
    assert "Good Morning" not in listed
    opened = client.get(f"/api/exercises/{good_morning['id']}", headers=headers).json()
    assert opened["retired"] is True
    assert len(client.get(f"/api/exercises/{good_morning['id']}/logs", headers=headers).json()) == 1
    recent = client.get("/api/exercises/recent", headers=headers).json()
    assert recent[0]["exercise"]["name"] == "Good Morning"


def test_rename_keeps_history(tmp_path, real_rows, client, signed_in):
    headers = signed_in()
    dip = next(
        e for e in client.get("/api/exercises", headers=headers).json() if e["name"] == "Dip"
    )
    client.post(
        f"/api/exercises/{dip['id']}/logs",
        json={"weight": 0, "reps": 12, "sets": 3},
        headers=headers,
    )

    rows = [("Parallel Bar Dip", e, m) if n == "Dip" else (n, e, m) for n, e, m in real_rows]
    write_catalog(tmp_path, rows, renames=[("Dip", "Parallel Bar Dip")])
    changes = run(tmp_path)
    assert changes.rename == [("Dip", "Parallel Bar Dip")]
    assert changes.add == [] and changes.retire == []

    renamed = client.get(f"/api/exercises/{dip['id']}", headers=headers).json()
    assert renamed["name"] == "Parallel Bar Dip"
    assert len(client.get(f"/api/exercises/{dip['id']}/logs", headers=headers).json()) == 1
    assert run(tmp_path).empty()  # the rename line is harmless once applied


def test_custom_exercises_untouched(tmp_path, real_rows, client, signed_in):
    headers = signed_in()
    client.post(
        "/api/exercises",
        json={"name": "My Lift", "equipment": "Other", "muscle_group": "Other"},
        headers=headers,
    )
    write_catalog(tmp_path, real_rows)
    assert run(tmp_path).empty()
    assert "My Lift" in [e["name"] for e in client.get("/api/exercises", headers=headers).json()]


@pytest.mark.parametrize(
    "rows, message",
    [
        ([("Squat", "Spaceship", "Legs")], "equipment"),
        ([("Squat", "Barbell", "Elbows")], "muscle_group"),
        ([("Squat", "Barbell", "Legs"), ("squat", "Barbell", "Legs")], "listed twice"),
        ([("", "Barbell", "Legs")], "name"),
    ],
)
def test_bad_csv_rejected(tmp_path, rows, message):
    write_catalog(tmp_path, rows)
    with pytest.raises(CatalogError, match=message):
        read_catalog(tmp_path)
