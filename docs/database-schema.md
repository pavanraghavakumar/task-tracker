# SQLite schema contract

The Flask application should create one `Database` per configured database path, call `migrate()` during application initialization, and create repository instances around it. Every repository opens a short-lived connection, enables foreign keys, uses bound parameters, commits successful writes, rolls back failed writes, and closes the connection.

## Stored values and serialization

- IDs are SQLite integer primary keys and are exposed as JSON numbers.
- Timestamps are UTC ISO-8601 strings such as `2026-11-07T14:12:00.000Z`.
- `due_date` is either `null` or an ISO calendar date (`YYYY-MM-DD`).
- Boolean `is_active` is stored as `0` or `1`; Flask should serialize it as a JSON boolean.
- Priority is one of `low`, `medium`, or `high`.
- Status is one of `pending`, `in_progress`, or `completed`.
- Passwords are never stored. Flask supplies a Werkzeug-compatible value in `password_hash` and must omit it from API responses.
- Task `details` is optional JSON text. `field_name`, `old_value`, and `new_value` describe individual changes.

## Tables

### `users`

`id`, case-insensitive unique `email`, `password_hash`, `name`, `is_active`, `created_at`, `updated_at`. Deleting a user cascades to owned categories, tasks, and activity. The application should normalize email to lowercase and hash passwords before calling `UserRepository.create()`.

### `categories`

`id`, nullable `user_id`, case-insensitive `name`, six-digit `color`, `created_at`, `updated_at`. A non-null owner represents a private category; `null` represents a global category visible to every user. Names are unique per owner, and global names are unique among global rows. A category referenced by a task cannot be deleted until the task is moved or deleted.

### `tasks`

`id`, required `user_id`, nullable `category_id`, `title`, `description`, `priority`, `status`, nullable `due_date`, nullable `completed_at`, `created_at`, `updated_at`. A completed task must have `completed_at`; all other statuses must have it unset. Repository validation prevents assigning another user's category while permitting global categories.

### `task_activity`

Append-only audit entries contain `id`, `task_id`, `user_id`, `action`, optional change fields and details, and `created_at`. Actions are `created`, `updated`, `status_changed`, `completed`, `reopened`, or `deleted`. Activity belongs to the same user as its task and is removed when the task is deleted, avoiding orphaned personal data.

## Repository contract for Flask

- `UserRepository`: `create`, `get`, `get_by_email`, `update`, `delete`.
- `CategoryRepository`: `create`, `list`, `update`, `delete`. `list` includes global categories.
- `TaskRepository`: `create`, `get`, `list`, `update`, `delete`, `dashboard`.
- `ActivityRepository`: `list_for_task`.
- Task list filtering accepts search text, arrays of statuses and priorities, category, due-date upper bound, safe sort column/direction, limit, and offset.
- Task reads include `category_name` and `category_color` from a left join.
- Dashboard output includes `total`, `pending`, `in_progress`, `completed`, `overdue`, and `upcoming_deadlines`.
- Missing records return `None`; delete methods return `bool`. SQLite uniqueness/check failures raise `sqlite3.IntegrityError`; a cross-user category assignment raises `ValueError`. Flask should map these to appropriate `404`, `409`, or `400` responses.

## Initialization

Run `python -m database.init_db instance/task_tracker.db --seed` from the repository root. Migrations are ordered SQL files recorded in `schema_migrations` and are safe to invoke repeatedly. The sample login is `demo@example.com` / `DemoPass123!`; it is development-only and its password is stored as a salted PBKDF2 hash.

## Index strategy

Indexes support user-scoped status, priority, category, due-date, and updated-time task queries plus reverse chronological activity lookup. Email and category uniqueness constraints create their own supporting indexes.
