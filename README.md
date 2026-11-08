# Personal Task Tracker

This repository integrates the Angular frontend, Flask REST API, and SQLite data layer into one local-only application.

## Requirements

- Python 3.11 or newer
- Node.js 20.19 or newer and npm 10 or newer

## First-time setup

Open two Command Prompt terminals at the repository root.

Backend terminal:

```text
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
set TASK_TRACKER_SECRET=replace-with-a-long-random-local-secret
set PORT=5001
python app.py
```

Frontend terminal:

```text
cd frontend
npm ci
npm start
```

Open `http://127.0.0.1:4200`. Angular proxies `/api` to Flask at `http://127.0.0.1:5001`; no cloud service or deployment is used. Port 5001 avoids the Windows service that commonly occupies port 5000. The backend creates `backend/task_tracker.db` automatically. Set `TASK_TRACKER_DATABASE` before starting Flask to use another local SQLite path.

## Checks

From the repository root:

```text
python -m pytest -q
cd frontend
npm run build
```

The Python suite covers the SQLite repositories, API, security boundaries, and cross-workstream contracts. The Angular production build type-checks and bundles the integrated client.

## Project structure

- `frontend/`: Angular UI and development proxy
- `backend/`: Flask API and its runtime SQLite schema
- `database/`: independently reusable migration, repositories, and sample-data utility
- `tests/`: database and cross-workstream integration checks
- `docs/`: schema, test, and workstream documentation

## Local data

The runtime database and authentication token are local. Delete `backend/task_tracker.db` only when you intentionally want to reset all local application data. Do not commit database files, secrets, virtual environments, or `node_modules`.
