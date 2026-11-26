# Exercise catalog

`exercises.csv` is the standard exercise list everyone sees. Edit it here (any spreadsheet app
or text editor works), then sync the database:

```powershell
cd backend
.venv\Scripts\python -m app.catalog          # shows what would change; writes nothing
.venv\Scripts\python -m app.catalog --apply  # makes the changes
```

Run it against each database (dev now; production once there is one) after `alembic upgrade
head`. The tests sync their own database from this file automatically.

| To... | Do this |
| --- | --- |
| **Add** an exercise | Add a row. |
| **Change** its equipment or muscle group | Edit the row. |
| **Remove** one | Delete the row. It's *retired*: gone from the list, but anyone who logged it keeps their history and can still open and log it. Nothing is ever deleted. |
| **Bring one back** | Add the row again. |
| **Rename** one | Change the name in `exercises.csv` *and* add `Old Name,New Name` to `renames.csv`. Everyone's history follows the new name. (Without the rename line, the old one would be retired and a new, empty one added.) |

Rules the sync checks (it stops and changes nothing if a row breaks one):

- `name`: 1–80 characters, each name once (ignoring case).
- `equipment`: Barbell, Dumbbell, Machine, Cable, Bodyweight, Kettlebell, Band, Other.
- `muscle_group`: Chest, Back, Legs, Shoulders, Arms, Core, Full body, Other.

These lists live in `backend/app/schemas.py` (and `frontend/src/lib/api.ts` for the custom
exercise form); change both together.

Custom exercises that users make for themselves are separate and never touched by the sync.
Merging two catalog exercises (moving everyone's logs from one to the other) isn't supported
yet; it's a card on the board.
