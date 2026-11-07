"""Parameterized CRUD repositories and reporting queries for Flask services."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from typing import Any, Mapping, Sequence

from .connection import Database


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class UserRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, email: str, password_hash: str, name: str) -> dict[str, Any]:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO users(email, password_hash, name) VALUES (?, ?, ?)",
                (email.strip().lower(), password_hash, name.strip()),
            )
            return dict(connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())

    def get(self, user_id: int) -> dict[str, Any] | None:
        with self.database.transaction() as connection:
            return _dict(connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        with self.database.transaction() as connection:
            return _dict(connection.execute("SELECT * FROM users WHERE email = ?", (email.strip(),)).fetchone())

    def update(self, user_id: int, **changes: Any) -> dict[str, Any] | None:
        allowed = {key: value for key, value in changes.items() if key in {"email", "password_hash", "name", "is_active"}}
        if not allowed:
            return self.get(user_id)
        assignments = ", ".join(f"{key} = ?" for key in allowed)
        with self.database.transaction() as connection:
            connection.execute(f"UPDATE users SET {assignments} WHERE id = ?", (*allowed.values(), user_id))
            return _dict(connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())

    def delete(self, user_id: int) -> bool:
        with self.database.transaction() as connection:
            return connection.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount == 1


class CategoryRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, user_id: int, name: str, color: str = "#64748B") -> dict[str, Any]:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO categories(user_id, name, color) VALUES (?, ?, ?)", (user_id, name.strip(), color)
            )
            return dict(connection.execute("SELECT * FROM categories WHERE id = ?", (cursor.lastrowid,)).fetchone())

    def list(self, user_id: int) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM categories WHERE user_id = ? OR user_id IS NULL ORDER BY name COLLATE NOCASE", (user_id,)
            )]

    def update(self, user_id: int, category_id: int, **changes: Any) -> dict[str, Any] | None:
        allowed = {key: value for key, value in changes.items() if key in {"name", "color"}}
        if allowed:
            assignments = ", ".join(f"{key} = ?" for key in allowed)
            with self.database.transaction() as connection:
                connection.execute(
                    f"UPDATE categories SET {assignments} WHERE id = ? AND user_id = ?",
                    (*allowed.values(), category_id, user_id),
                )
                return _dict(connection.execute(
                    "SELECT * FROM categories WHERE id = ? AND user_id = ?", (category_id, user_id)
                ).fetchone())
        return next((item for item in self.list(user_id) if item["id"] == category_id), None)

    def delete(self, user_id: int, category_id: int) -> bool:
        with self.database.transaction() as connection:
            return connection.execute(
                "DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, user_id)
            ).rowcount == 1


class TaskRepository:
    WRITABLE = {"category_id", "title", "description", "priority", "status", "due_date"}
    SORT_COLUMNS = {"created_at", "updated_at", "due_date", "title", "priority", "status"}

    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, user_id: int, title: str, **values: Any) -> dict[str, Any]:
        data = {key: value for key, value in values.items() if key in self.WRITABLE}
        data["title"] = title.strip()
        if data.get("status") == "completed":
            data["completed_at"] = _utc_sql()
        columns = ["user_id", *data.keys()]
        placeholders = ", ".join("?" for _ in columns)
        with self.database.transaction() as connection:
            self._validate_category(connection, user_id, data.get("category_id"))
            cursor = connection.execute(
                f"INSERT INTO tasks({', '.join(columns)}) VALUES ({placeholders})", (user_id, *data.values())
            )
            task_id = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO task_activity(task_id, user_id, action, details) VALUES (?, ?, 'created', ?)",
                (task_id, user_id, json.dumps({"title": data["title"]})),
            )
            return self._get(connection, user_id, task_id)

    def get(self, user_id: int, task_id: int) -> dict[str, Any] | None:
        with self.database.transaction() as connection:
            row = connection.execute(self._select() + " WHERE t.user_id = ? AND t.id = ?", (user_id, task_id)).fetchone()
            return _dict(row)

    def list(
        self,
        user_id: int,
        *,
        search: str | None = None,
        statuses: Sequence[str] | None = None,
        priorities: Sequence[str] | None = None,
        category_id: int | None = None,
        due_before: str | None = None,
        sort_by: str = "created_at",
        direction: str = "desc",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses, parameters = ["t.user_id = ?"], [user_id]
        if search:
            clauses.append("(t.title LIKE ? ESCAPE '\\' OR t.description LIKE ? ESCAPE '\\')")
            escaped = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            parameters.extend((escaped, escaped))
        for column, values in (("status", statuses), ("priority", priorities)):
            if values:
                clauses.append(f"t.{column} IN ({', '.join('?' for _ in values)})")
                parameters.extend(values)
        if category_id is not None:
            clauses.append("t.category_id = ?")
            parameters.append(category_id)
        if due_before:
            clauses.append("t.due_date <= ?")
            parameters.append(due_before)
        order = sort_by if sort_by in self.SORT_COLUMNS else "created_at"
        order_direction = "ASC" if direction.lower() == "asc" else "DESC"
        parameters.extend((min(max(limit, 1), 500), max(offset, 0)))
        sql = self._select() + f" WHERE {' AND '.join(clauses)} ORDER BY t.{order} {order_direction}, t.id DESC LIMIT ? OFFSET ?"
        with self.database.transaction() as connection:
            return [dict(row) for row in connection.execute(sql, parameters)]

    def update(self, user_id: int, task_id: int, **changes: Any) -> dict[str, Any] | None:
        allowed = {key: value for key, value in changes.items() if key in self.WRITABLE}
        with self.database.transaction() as connection:
            old = connection.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).fetchone()
            if old is None:
                return None
            if "category_id" in allowed:
                self._validate_category(connection, user_id, allowed["category_id"])
            if "status" in allowed:
                allowed["completed_at"] = _utc_sql() if allowed["status"] == "completed" else None
            changed = {key: value for key, value in allowed.items() if value != old[key]}
            if not changed:
                return self._get(connection, user_id, task_id)
            assignments = ", ".join(f"{key} = ?" for key in changed)
            connection.execute(f"UPDATE tasks SET {assignments} WHERE id = ? AND user_id = ?", (*changed.values(), task_id, user_id))
            for field, value in changed.items():
                if field == "completed_at":
                    continue
                action = "updated"
                if field == "status":
                    action = "completed" if value == "completed" else ("reopened" if old[field] == "completed" else "status_changed")
                connection.execute(
                    "INSERT INTO task_activity(task_id, user_id, action, field_name, old_value, new_value) VALUES (?, ?, ?, ?, ?, ?)",
                    (task_id, user_id, action, field, old[field], value),
                )
            return self._get(connection, user_id, task_id)

    def delete(self, user_id: int, task_id: int) -> bool:
        with self.database.transaction() as connection:
            return connection.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).rowcount == 1

    def dashboard(self, user_id: int, upcoming_days: int = 7) -> dict[str, Any]:
        today, upcoming = date.today(), date.today() + timedelta(days=upcoming_days)
        with self.database.transaction() as connection:
            counts = dict(connection.execute(
                "SELECT COUNT(*) total, SUM(status = 'pending') pending, SUM(status = 'in_progress') in_progress, "
                "SUM(status = 'completed') completed, SUM(status <> 'completed' AND due_date < ?) overdue "
                "FROM tasks WHERE user_id = ?", (today.isoformat(), user_id)
            ).fetchone())
            deadlines = [dict(row) for row in connection.execute(
                self._select() + " WHERE t.user_id = ? AND t.status <> 'completed' AND t.due_date BETWEEN ? AND ? "
                "ORDER BY t.due_date ASC, t.priority DESC", (user_id, today.isoformat(), upcoming.isoformat())
            )]
            return {**{key: value or 0 for key, value in counts.items()}, "upcoming_deadlines": deadlines}

    @staticmethod
    def _select() -> str:
        return "SELECT t.*, c.name category_name, c.color category_color FROM tasks t LEFT JOIN categories c ON c.id = t.category_id"

    @classmethod
    def _get(cls, connection: sqlite3.Connection, user_id: int, task_id: int) -> dict[str, Any]:
        return dict(connection.execute(cls._select() + " WHERE t.user_id = ? AND t.id = ?", (user_id, task_id)).fetchone())

    @staticmethod
    def _validate_category(connection: sqlite3.Connection, user_id: int, category_id: int | None) -> None:
        if category_id is None:
            return
        category = connection.execute("SELECT user_id FROM categories WHERE id = ?", (category_id,)).fetchone()
        if category is None or category["user_id"] not in (None, user_id):
            raise ValueError("category does not exist or belongs to another user")


class ActivityRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_for_task(self, user_id: int, task_id: int, limit: int = 100) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM task_activity WHERE user_id = ? AND task_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (user_id, task_id, min(max(limit, 1), 500)),
            )]


def _utc_sql() -> str:
    """Return a SQLite-formatted UTC timestamp from SQLite's own clock."""
    connection = sqlite3.connect(":memory:")
    try:
        return str(connection.execute("SELECT strftime('%Y-%m-%dT%H:%M:%fZ', 'now')").fetchone()[0])
    finally:
        connection.close()
