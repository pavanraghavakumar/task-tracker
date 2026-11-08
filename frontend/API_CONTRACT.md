# Frontend API Contract

This contract allows the Angular and Flask workstreams to develop independently. All endpoints are relative to `/api/v1`, use JSON, and return a common response envelope.

## Conventions

- Protected endpoints require `Authorization: Bearer <access_token>`.
- Dates use `YYYY-MM-DD`; timestamps use ISO 8601 UTC strings.
- Success: `{ "success": true, "data": ..., "message": "optional" }`
- Error: `{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "Readable message", "details": {} } }`
- Validation errors should use HTTP 400 or 422, unauthenticated requests 401, forbidden requests 403, missing resources 404, conflicts 409, and unexpected failures 500.
- Every task/category resource must be scoped to the authenticated user.

## Domain values

- Priority: `low | medium | high`
- Status: `pending | in_progress | completed`
- Category: `{ id, name, color, task_count? }`, where color is a `#RRGGBB` string.
- Task: `{ id, title, description, category, priority, status, due_date, completed_at, created_at, updated_at }`.

## Authentication

### `POST /auth/register`

Request: `{ "name": "Alex Morgan", "email": "alex@example.com", "password": "Secret123" }`

### `POST /auth/login`

Request: `{ "email": "alex@example.com", "password": "Secret123" }`

Both return `{ access_token, user: { id, name, email, created_at } }` in `data`. Registration creates and authenticates the user in one operation.

## Dashboard

### `GET /dashboard`

Returns `{ counts: { total, pending, in_progress, completed, overdue }, completion_percentage, upcoming_deadlines }`. `completion_percentage` is a number from 0 to 100; `upcoming_deadlines` is an array of full task objects ordered by ascending due date. The Angular API adapter maps this response to the dashboard view model.

## Tasks

### `GET /tasks`

Supported query parameters:

- `search`: case-insensitive title/description search
- `status`, `priority`, `category_id`
- `due_before`, `due_after`
- `sort_by`: `title | priority | status | due_date | created_at | updated_at`
- `sort_order`: `asc | desc`
- `page`, `per_page`

Returns `{ items: Task[], pagination: { page, per_page, total, pages } }`.

### `GET /tasks/:id`

Returns one task.

### `POST /tasks`

### `PATCH /tasks/:id`

Request body: `{ title, description, category_id, priority, status, due_date }`. `category_id` and `due_date` may be `null`. The update endpoint accepts complete or partial fields. Both return the resulting task.

### `DELETE /tasks/:id`

Returns a successful envelope with `data: null`.

## Categories

- `GET /categories` returns categories ordered by name, including `task_count`.
- `POST /categories` accepts `{ name, color }` and returns the category.
- `PATCH /categories/:id` accepts `{ name, color }` and returns the category.
- `DELETE /categories/:id` leaves associated tasks uncategorized and returns `data: null`.

Category names should be unique per user, case-insensitively.

## Integration notes

The Angular client deliberately performs no client-side mock responses. Integration should proxy `/api` to the local Flask server or serve both applications behind the same local origin. CORS is only needed if the integration workstream chooses separate origins. A 401 response on an authenticated request clears local authentication and routes the user to login.
