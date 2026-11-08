# Flask backend

## Local setup

From `backend` on Python 3.11 or newer:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
set TASK_TRACKER_SECRET=replace-with-a-long-random-secret
python app.py
```

The server creates `task_tracker.db` from `schema.sql` and listens at `http://127.0.0.1:5000`. Set `TASK_TRACKER_DATABASE` to choose another SQLite file. Set `FLASK_DEBUG=1` only for local development.

Run checks from this directory with `python -m pytest -q`.

## Structure

- `app.py`: application factory, authentication, validation, routes, SQLite adapter, and consistent error handling.
- `schema.sql`: independently consumable data contract.
- `API.md`: frontend and database integration contract.
- `tests/test_api.py`: authentication, authorization, task/category lifecycle, filters, activity, dashboard, validation, and error response checks.

