"""Keeps the shared exercise catalog in step with catalog/exercises.csv.

    python -m app.catalog            show what would change (nothing is written)
    python -m app.catalog --apply    make the changes

Edit catalog/exercises.csv to add an exercise, change its equipment or muscle group, or remove
it. To rename one, change its name in exercises.csv *and* add a line to catalog/renames.csv
(old_name,new_name), so everyone's history moves with it instead of the old one being retired
and a new one added.

Nothing is ever deleted: an exercise missing from the CSV is retired (hidden from the list, but
anyone who logged it keeps their history and can still open it). Putting it back un-retires it.
Custom exercises (user_id set) are never touched.
"""

import csv
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Exercise
from app.schemas import EQUIPMENT, MUSCLE_GROUPS

CATALOG_DIR = Path(__file__).resolve().parent.parent / "catalog"


class CatalogError(ValueError):
    pass


@dataclass
class Plan:
    add: list[tuple[str, str, str]] = field(default_factory=list)
    rename: list[tuple[str, str]] = field(default_factory=list)
    update: list[tuple[str, str, str]] = field(default_factory=list)
    restore: list[str] = field(default_factory=list)
    retire: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def empty(self) -> bool:
        return not (self.add or self.rename or self.update or self.restore or self.retire)

    def lines(self) -> list[str]:
        out = [f"+ add      {n} ({e}, {m})" for n, e, m in self.add]
        out += [f"~ rename   {old} -> {new}" for old, new in self.rename]
        out += [f"~ update   {n} -> {e}, {m}" for n, e, m in self.update]
        out += [f"+ restore  {n}" for n in self.restore]
        out += [f"- retire   {n}" for n in self.retire]
        out += [f"! skipped  {s}" for s in self.skipped]
        return out


def read_catalog(
    directory: Path = CATALOG_DIR,
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]]]:
    """Reads and checks both CSVs. Raises CatalogError naming the bad line."""
    rows: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    with open(directory / "exercises.csv", newline="", encoding="utf-8") as f:
        for line, row in enumerate(csv.DictReader(f), start=2):
            name = " ".join((row.get("name") or "").split())
            equipment = (row.get("equipment") or "").strip()
            muscle = (row.get("muscle_group") or "").strip()
            where = f"exercises.csv line {line}"
            if not name or len(name) > 80:
                raise CatalogError(f"{where}: name must be 1-80 characters")
            if equipment not in EQUIPMENT:
                raise CatalogError(f"{where}: equipment {equipment!r} isn't one of {EQUIPMENT}")
            if muscle not in MUSCLE_GROUPS:
                raise CatalogError(f"{where}: muscle_group {muscle!r} isn't one of {MUSCLE_GROUPS}")
            if name.lower() in seen:
                raise CatalogError(f"{where}: {name!r} is listed twice")
            seen.add(name.lower())
            rows.append((name, equipment, muscle))

    renames: list[tuple[str, str]] = []
    path = directory / "renames.csv"
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for line, row in enumerate(csv.DictReader(f), start=2):
                old = " ".join((row.get("old_name") or "").split())
                new = " ".join((row.get("new_name") or "").split())
                if not old or not new:
                    raise CatalogError(f"renames.csv line {line}: needs old_name and new_name")
                renames.append((old, new))
    return rows, renames


def plan(db: Session, rows, renames) -> Plan:
    """Works out the changes without writing anything."""
    result = Plan()
    catalog = {
        e.name.lower(): e for e in db.scalars(select(Exercise).where(Exercise.user_id.is_(None)))
    }
    wanted = {name.lower() for name, _, _ in rows}

    # Renames first, so the rows below find the exercise under its new name.
    renamed: dict[str, Exercise] = {}
    for old, new in renames:
        current = catalog.get(old.lower())
        if current is None:
            continue  # already applied, or never existed
        if new.lower() in catalog and catalog[new.lower()] is not current:
            result.skipped.append(f"rename {old} -> {new}: both exist (merge them instead)")
            continue
        if new.lower() not in wanted:
            result.skipped.append(f"rename {old} -> {new}: {new} isn't in exercises.csv")
            continue
        if current.name != new:
            result.rename.append((current.name, new))
        renamed[new.lower()] = current
        del catalog[old.lower()]

    for name, equipment, muscle in rows:
        existing = renamed.get(name.lower()) or catalog.get(name.lower())
        if existing is None:
            result.add.append((name, equipment, muscle))
            continue
        if (existing.equipment, existing.muscle_group) != (equipment, muscle):
            result.update.append((name, equipment, muscle))
        if existing.retired_at is not None:
            result.restore.append(name)

    for key, e in catalog.items():
        if key not in wanted and e.retired_at is None:
            result.retire.append(e.name)
    return result


def apply(db: Session, changes: Plan) -> None:
    now = datetime.now(UTC)
    by_name = lambda name: db.scalar(  # noqa: E731
        select(Exercise).where(
            Exercise.user_id.is_(None), func.lower(Exercise.name) == name.lower()
        )
    )
    for old, new in changes.rename:
        by_name(old).name = new
    db.flush()
    for name, equipment, muscle in changes.update:
        e = by_name(name)
        e.equipment, e.muscle_group = equipment, muscle
    for name in changes.restore:
        by_name(name).retired_at = None
    for name in changes.retire:
        by_name(name).retired_at = now
    for name, equipment, muscle in changes.add:
        db.add(Exercise(name=name, equipment=equipment, muscle_group=muscle))
    db.commit()


def sync(db: Session, write: bool, directory: Path = CATALOG_DIR) -> Plan:
    rows, renames = read_catalog(directory)
    changes = plan(db, rows, renames)
    if write and not changes.empty():
        apply(db, changes)
    return changes


def main(argv: list[str]) -> int:
    from app.db import get_db

    write = "--apply" in argv
    db = next(get_db())
    try:
        changes = sync(db, write)
    except CatalogError as err:
        print(f"Catalog not changed: {err}")
        return 1
    for line in changes.lines():
        print(line)
    if changes.empty():
        print("Catalog already matches exercises.csv.")
    elif not write:
        print("\nNothing written. Run again with --apply to make these changes.")
    else:
        print("\nApplied.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
