# Personal Task Tracker API contract

Base URL: `http://127.0.0.1:5000/api/v1`. JSON is used for requests and responses. Protected endpoints require `Authorization: Bearer <access_token>`. Angular development origin `http://localhost:4200` is allowed by default.

## Response convention

Success: `{ "success": true, "data": ..., "message": "optional" }`.

Error: `{ "success": false, "error": { "code": "validation_error", "message": "...", "details": {...} } }`.

The API uses `200` for successful reads/updates/deletes, `201` for creation, `400` for invalid input, `401` for authentication failure, `404` for inaccessible resources, `409` for uniqueness conflicts, `415` for non-JSON request bodies, and `500` for unexpected failures.

## Authentication

| Method | Path | Body / result |
|---|---|---|
| POST | `/auth/register` | Body: `name`, `email`, `password` (8-128 chars, letter and digit). Returns `user`, JWT `access_token`, `token_type`, `expires_in`. |
| POST | `/auth/login` | Body: `email`, `password`. Returns the same authentication payload. |
| GET | `/auth/me` | Returns the authenticated user. |

Passwords are stored using Werkzeug's salted `scrypt` password hashing. Tokens are HS256 JWTs with one-hour expiry. Set a strong `TASK_TRACKER_SECRET` outside development; tokens are stateless and logout is performed client-side by deleting the token.

## Categories

| Method | Path | Contract |
|---|---|---|
| GET | `/categories` | Lists user-owned and global (`user_id=null`) categories, including `task_count`. |
| POST | `/categories` | Body: `name` (1-50 chars), optional `color` (`#RRGGBB`). |
| PATCH | `/categories/{id}` | Updates one or both of `name`, `color`; only owner-created categories are mutable. |
| DELETE | `/categories/{id}` | Deletes an owned category; linked task category values become null. |

## Tasks

A task contains `id`, `title`, `description`, `priority`, `status`, `due_date`, `completed_at`, nested `category`, `created_at`, and `updated_at`. Priorities are `low`, `medium`, `high`. Statuses are `pending`, `in_progress`, `completed`. Dates are `YYYY-MM-DD`; timestamps are ISO-8601 UTC.

| Method | Path | Contract |
|---|---|---|
| GET | `/tasks` | Paginated task list. Query parameters documented below. |
| POST | `/tasks` | Body: required `title`; optional `description`, `priority`, `status`, `due_date`, `category_id`. |
| GET | `/tasks/{id}` | Returns one owned task. |
| PATCH | `/tasks/{id}` | Partial update using task creation fields. Completing sets `completed_at`; reopening clears it. |
| DELETE | `/tasks/{id}` | Deletes one owned task. |
| GET | `/tasks/{id}/activity` | Returns newest-first creation/update activity. |

Task-list query parameters:

- `search`: case-insensitive title/description substring.
- `status` and `priority`: one value or comma-separated values.
- `category_id`, `due_before`, `due_after`.
- `sort_by`: `created_at`, `updated_at`, `due_date`, `title`, `priority`, or `status`.
- `sort_order`: `asc` or `desc`; `page` defaults to 1 and `per_page` defaults to 20 (maximum 100).

List data is `{ "items": [...], "pagination": { "page", "per_page", "total", "pages" } }`.

## Dashboard and health

`GET /dashboard` returns `counts` (`total`, `pending`, `in_progress`, `completed`, `overdue`), `completion_percentage`, and up to ten non-completed `upcoming_deadlines` due today through seven days from today. `GET /health` is public and verifies database connectivity.

## SQLite data contract

The canonical independent contract is in `schema.sql`:

- `users`: case-insensitive unique email, display name, password hash, timestamps.
- `categories`: nullable owner for global categories, owner/name uniqueness, color, timestamps.
- `tasks`: owner, optional category, title/description, constrained priority/status, due and completion dates, timestamps.
- `task_activity`: task/user, action, JSON-encoded details, timestamp.

SQLite foreign keys must be enabled on every connection. Required delete behavior is user cascade, category-to-task `SET NULL`, and task-to-activity cascade. Existing indexes cover the list and dashboard access paths. The database workstream can provide the same schema and repositories without changing this HTTP contract.

