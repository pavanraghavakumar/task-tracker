"""Personal Task Tracker REST API.

The module intentionally depends only on its documented SQLite contract, so it
can be developed and tested independently from the Angular and database
workstreams.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import base64
import hashlib
import hmac
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
PRIORITIES = {"low", "medium", "high"}
STATUSES = {"pending", "in_progress", "completed"}
SORT_COLUMNS = {
    "created_at": "t.created_at",
    "updated_at": "t.updated_at",
    "due_date": "t.due_date",
    "title": "LOWER(t.title)",
    "priority": "CASE t.priority WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END",
    "status": "CASE t.status WHEN 'pending' THEN 1 WHEN 'in_progress' THEN 2 ELSE 3 END",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def success(data: Any = None, message: str | None = None, status: int = 200):
    body: dict[str, Any] = {"success": True, "data": data}
    if message:
        body["message"] = message
    return jsonify(body), status


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def init_db() -> None:
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    get_db().executescript(schema)
    get_db().commit()


def require_json() -> dict[str, Any]:
    if not request.is_json:
        raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json")
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError(400, "invalid_json", "Request body must be a JSON object")
    return body


def reject_unknown(body: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(body) - allowed)
    if unknown:
        raise ApiError(400, "validation_error", "Request contains unknown fields", {"fields": unknown})


def parse_date(value: Any, field: str = "due_date") -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ApiError(400, "validation_error", f"{field} must be an ISO date (YYYY-MM-DD)")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ApiError(400, "validation_error", f"{field} must be a valid ISO date (YYYY-MM-DD)") from exc


def issue_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": str(user_id), "iat": int(now.timestamp()), "exp": int((now + current_app.config["JWT_TTL"]).timestamp())}

    def encode(value: dict[str, Any]) -> str:
        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    signing_input = f"{encode(header)}.{encode(payload)}"
    signature = hmac.new(current_app.config["SECRET_KEY"].encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}"
        expected = hmac.new(current_app.config["SECRET_KEY"].encode(), signing_input.encode(), hashlib.sha256).digest()
        supplied = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("invalid signature")
        header = json.loads(base64.urlsafe_b64decode(header_part + "=" * (-len(header_part) % 4)))
        payload = json.loads(base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4)))
        if header != {"alg": "HS256", "typ": "JWT"} or not isinstance(payload.get("exp"), int):
            raise ValueError("invalid token structure")
        if payload["exp"] <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired token")
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ApiError(401, "invalid_token", "The access token is invalid or expired") from exc


def auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise ApiError(401, "authentication_required", "A Bearer token is required")
        try:
            payload = decode_token(header[7:])
            g.user_id = int(payload["sub"])
        except (ApiError, KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, ApiError):
                raise
            raise ApiError(401, "invalid_token", "The access token is invalid or expired") from exc
        user = get_db().execute("SELECT id FROM users WHERE id = ?", (g.user_id,)).fetchone()
        if not user:
            raise ApiError(401, "invalid_token", "The token user no longer exists")
        return view(*args, **kwargs)

    return wrapped


def serialize_category(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None or row["category_id"] is None:
        return None
    return {"id": row["category_id"], "name": row["category_name"], "color": row["category_color"]}


def serialize_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "priority": row["priority"],
        "status": row["status"],
        "due_date": row["due_date"],
        "completed_at": row["completed_at"],
        "category": serialize_category(row),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


TASK_SELECT = """
SELECT t.*, c.id AS category_id, c.name AS category_name, c.color AS category_color
FROM tasks t LEFT JOIN categories c ON c.id = t.category_id
"""


def get_owned_task(task_id: int) -> sqlite3.Row:
    row = get_db().execute(TASK_SELECT + " WHERE t.id = ? AND t.user_id = ?", (task_id, g.user_id)).fetchone()
    if not row:
        raise ApiError(404, "task_not_found", "Task not found")
    return row


def validate_category(category_id: Any) -> int | None:
    if category_id is None:
        return None
    if isinstance(category_id, bool) or not isinstance(category_id, int):
        raise ApiError(400, "validation_error", "category_id must be an integer or null")
    row = get_db().execute(
        "SELECT id FROM categories WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
        (category_id, g.user_id),
    ).fetchone()
    if not row:
        raise ApiError(400, "invalid_category", "Category does not exist or is not accessible")
    return category_id


def log_activity(task_id: int, action: str, details: dict[str, Any] | None = None) -> None:
    get_db().execute(
        "INSERT INTO task_activity(task_id,user_id,action,details,created_at) VALUES(?,?,?,?,?)",
        (task_id, g.user_id, action, json.dumps(details or {}, separators=(",", ":")), utc_now()),
    )


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("TASK_TRACKER_DATABASE", str(Path(__file__).with_name("task_tracker.db"))),
        SECRET_KEY=os.environ.get("TASK_TRACKER_SECRET", "change-this-local-development-secret"),
        JWT_TTL=timedelta(hours=1),
        MAX_CONTENT_LENGTH=1_000_000,
    )
    if config:
        app.config.update(config)
    @app.after_request
    def add_cors_headers(response):
        allowed_origin = app.config.get("CORS_ORIGINS", "http://localhost:4200")
        if request.headers.get("Origin") == allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        return response

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.errorhandler(ApiError)
    def api_error(error: ApiError):
        return jsonify({"success": False, "error": {"code": error.code, "message": error.message, "details": error.details}}), error.status

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        return jsonify({"success": False, "error": {"code": error.name.lower().replace(" ", "_"), "message": error.description, "details": None}}), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error: Exception):
        app.logger.exception("Unhandled API error", exc_info=error)
        return jsonify({"success": False, "error": {"code": "internal_error", "message": "An unexpected error occurred", "details": None}}), 500

    @app.get("/api/v1/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return success({"status": "healthy"})

    @app.post("/api/v1/auth/register")
    def register():
        body = require_json()
        reject_unknown(body, {"name", "email", "password"})
        name = body.get("name", "").strip() if isinstance(body.get("name"), str) else ""
        email = body.get("email", "").strip().lower() if isinstance(body.get("email"), str) else ""
        password = body.get("password", "")
        errors = {}
        if not 2 <= len(name) <= 100:
            errors["name"] = "Name must contain 2 to 100 characters"
        if len(email) > 254 or not EMAIL_RE.fullmatch(email):
            errors["email"] = "A valid email address is required"
        if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
            errors["password"] = "Password must contain 8 to 128 characters"
        elif not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            errors["password"] = "Password must contain at least one letter and one number"
        if errors:
            raise ApiError(400, "validation_error", "Registration data is invalid", errors)
        now = utc_now()
        try:
            cursor = get_db().execute(
                "INSERT INTO users(email,name,password_hash,created_at,updated_at) VALUES(?,?,?,?,?)",
                (email, name, generate_password_hash(password), now, now),
            )
            get_db().commit()
        except sqlite3.IntegrityError as exc:
            raise ApiError(409, "email_exists", "An account with this email already exists") from exc
        user = {"id": cursor.lastrowid, "email": email, "name": name, "created_at": now}
        return success({"user": user, "access_token": issue_token(cursor.lastrowid), "token_type": "Bearer", "expires_in": int(app.config["JWT_TTL"].total_seconds())}, "Registration successful", 201)

    @app.post("/api/v1/auth/login")
    def login():
        body = require_json()
        reject_unknown(body, {"email", "password"})
        email = body.get("email", "").strip().lower() if isinstance(body.get("email"), str) else ""
        password = body.get("password", "")
        row = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row or not isinstance(password, str) or not check_password_hash(row["password_hash"], password):
            raise ApiError(401, "invalid_credentials", "Email or password is incorrect")
        user = {"id": row["id"], "email": row["email"], "name": row["name"], "created_at": row["created_at"]}
        return success({"user": user, "access_token": issue_token(row["id"]), "token_type": "Bearer", "expires_in": int(app.config["JWT_TTL"].total_seconds())}, "Login successful")

    @app.get("/api/v1/auth/me")
    @auth_required
    def me():
        row = get_db().execute("SELECT id,email,name,created_at,updated_at FROM users WHERE id = ?", (g.user_id,)).fetchone()
        return success(dict(row))

    @app.get("/api/v1/categories")
    @auth_required
    def list_categories():
        rows = get_db().execute(
            """SELECT c.id,c.name,c.color,c.user_id,c.created_at,c.updated_at,COUNT(t.id) task_count
               FROM categories c LEFT JOIN tasks t ON t.category_id=c.id AND t.user_id=?
               WHERE c.user_id=? OR c.user_id IS NULL GROUP BY c.id ORDER BY LOWER(c.name)""",
            (g.user_id, g.user_id),
        ).fetchall()
        return success([dict(row) for row in rows])

    @app.post("/api/v1/categories")
    @auth_required
    def create_category():
        body = require_json()
        reject_unknown(body, {"name", "color"})
        name = body.get("name", "").strip() if isinstance(body.get("name"), str) else ""
        color = body.get("color", "#64748B")
        if not 1 <= len(name) <= 50 or not isinstance(color, str) or not COLOR_RE.fullmatch(color):
            raise ApiError(400, "validation_error", "Category name (1-50 chars) and color (#RRGGBB) are required")
        now = utc_now()
        try:
            cursor = get_db().execute("INSERT INTO categories(user_id,name,color,created_at,updated_at) VALUES(?,?,?,?,?)", (g.user_id, name, color.upper(), now, now))
            get_db().commit()
        except sqlite3.IntegrityError as exc:
            raise ApiError(409, "category_exists", "A category with this name already exists") from exc
        return success({"id": cursor.lastrowid, "name": name, "color": color.upper(), "user_id": g.user_id, "task_count": 0, "created_at": now, "updated_at": now}, "Category created", 201)

    @app.route("/api/v1/categories/<int:category_id>", methods=["PATCH", "DELETE"])
    @auth_required
    def category_detail(category_id: int):
        row = get_db().execute("SELECT * FROM categories WHERE id=? AND user_id=?", (category_id, g.user_id)).fetchone()
        if not row:
            raise ApiError(404, "category_not_found", "Category not found")
        if request.method == "DELETE":
            get_db().execute("DELETE FROM categories WHERE id=?", (category_id,))
            get_db().commit()
            return success(None, "Category deleted")
        body = require_json()
        reject_unknown(body, {"name", "color"})
        name = body.get("name", row["name"])
        color = body.get("color", row["color"])
        name = name.strip() if isinstance(name, str) else ""
        if not body or not 1 <= len(name) <= 50 or not isinstance(color, str) or not COLOR_RE.fullmatch(color):
            raise ApiError(400, "validation_error", "At least one valid category field is required")
        now = utc_now()
        try:
            get_db().execute("UPDATE categories SET name=?,color=?,updated_at=? WHERE id=?", (name, color.upper(), now, category_id))
            get_db().commit()
        except sqlite3.IntegrityError as exc:
            raise ApiError(409, "category_exists", "A category with this name already exists") from exc
        return success({"id": category_id, "name": name, "color": color.upper(), "user_id": g.user_id, "updated_at": now}, "Category updated")

    @app.get("/api/v1/tasks")
    @auth_required
    def list_tasks():
        where = ["t.user_id = ?"]
        params: list[Any] = [g.user_id]
        for key, allowed in (("status", STATUSES), ("priority", PRIORITIES)):
            value = request.args.get(key)
            if value:
                values = value.split(",")
                if any(item not in allowed for item in values):
                    raise ApiError(400, "validation_error", f"Invalid {key} filter")
                where.append(f"t.{key} IN ({','.join('?' for _ in values)})")
                params.extend(values)
        category_id = request.args.get("category_id")
        if category_id:
            try:
                params.append(int(category_id))
            except ValueError as exc:
                raise ApiError(400, "validation_error", "category_id must be an integer") from exc
            where.append("t.category_id = ?")
        search = request.args.get("search", "").strip()
        if search:
            where.append("(LOWER(t.title) LIKE ? OR LOWER(t.description) LIKE ?)")
            term = f"%{search.lower()}%"
            params.extend([term, term])
        for key, operator in (("due_before", "<="), ("due_after", ">=")):
            value = request.args.get(key)
            if value:
                where.append(f"t.due_date {operator} ?")
                params.append(parse_date(value, key))
        sort_by = request.args.get("sort_by", "created_at")
        sort_order = request.args.get("sort_order", "desc").lower()
        if sort_by not in SORT_COLUMNS or sort_order not in {"asc", "desc"}:
            raise ApiError(400, "validation_error", "Invalid sort_by or sort_order")
        try:
            page = int(request.args.get("page", "1"))
            per_page = int(request.args.get("per_page", "20"))
        except ValueError as exc:
            raise ApiError(400, "validation_error", "page and per_page must be integers") from exc
        if page < 1 or per_page < 1 or per_page > 100:
            raise ApiError(400, "validation_error", "page must be >= 1 and per_page must be 1-100")
        clause = " AND ".join(where)
        total = get_db().execute(f"SELECT COUNT(*) FROM tasks t WHERE {clause}", params).fetchone()[0]
        rows = get_db().execute(
            TASK_SELECT + f" WHERE {clause} ORDER BY {SORT_COLUMNS[sort_by]} {sort_order.upper()}, t.id DESC LIMIT ? OFFSET ?",
            [*params, per_page, (page - 1) * per_page],
        ).fetchall()
        return success({"items": [serialize_task(row) for row in rows], "pagination": {"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page}})

    @app.post("/api/v1/tasks")
    @auth_required
    def create_task():
        body = require_json()
        reject_unknown(body, {"title", "description", "priority", "status", "due_date", "category_id"})
        title = body.get("title", "").strip() if isinstance(body.get("title"), str) else ""
        description = body.get("description", "")
        priority = body.get("priority", "medium")
        status_value = body.get("status", "pending")
        if not 1 <= len(title) <= 200 or not isinstance(description, str) or len(description) > 5000:
            raise ApiError(400, "validation_error", "Title (1-200 chars) and description (max 5000 chars) are required")
        if priority not in PRIORITIES or status_value not in STATUSES:
            raise ApiError(400, "validation_error", "Invalid priority or status")
        category_id = validate_category(body.get("category_id"))
        due_date = parse_date(body.get("due_date"))
        now = utc_now()
        completed_at = now if status_value == "completed" else None
        cursor = get_db().execute(
            """INSERT INTO tasks(user_id,category_id,title,description,priority,status,due_date,completed_at,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (g.user_id, category_id, title, description, priority, status_value, due_date, completed_at, now, now),
        )
        log_activity(cursor.lastrowid, "created", {"status": status_value})
        get_db().commit()
        return success(serialize_task(get_owned_task(cursor.lastrowid)), "Task created", 201)

    @app.get("/api/v1/tasks/<int:task_id>")
    @auth_required
    def task_detail(task_id: int):
        return success(serialize_task(get_owned_task(task_id)))

    @app.patch("/api/v1/tasks/<int:task_id>")
    @auth_required
    def update_task(task_id: int):
        row = get_owned_task(task_id)
        body = require_json()
        allowed = {"title", "description", "priority", "status", "due_date", "category_id"}
        reject_unknown(body, allowed)
        if not body:
            raise ApiError(400, "validation_error", "At least one task field is required")
        values = {key: row[key] for key in allowed}
        values.update(body)
        title = values["title"].strip() if isinstance(values["title"], str) else ""
        if not 1 <= len(title) <= 200 or not isinstance(values["description"], str) or len(values["description"]) > 5000:
            raise ApiError(400, "validation_error", "Invalid title or description")
        if values["priority"] not in PRIORITIES or values["status"] not in STATUSES:
            raise ApiError(400, "validation_error", "Invalid priority or status")
        values["category_id"] = validate_category(values["category_id"])
        values["due_date"] = parse_date(values["due_date"])
        now = utc_now()
        completed_at = row["completed_at"]
        if values["status"] == "completed" and row["status"] != "completed":
            completed_at = now
        elif values["status"] != "completed":
            completed_at = None
        get_db().execute(
            """UPDATE tasks SET category_id=?,title=?,description=?,priority=?,status=?,due_date=?,completed_at=?,updated_at=?
               WHERE id=? AND user_id=?""",
            (values["category_id"], title, values["description"], values["priority"], values["status"], values["due_date"], completed_at, now, task_id, g.user_id),
        )
        changes = {key: body[key] for key in body}
        log_activity(task_id, "updated", changes)
        get_db().commit()
        return success(serialize_task(get_owned_task(task_id)), "Task updated")

    @app.delete("/api/v1/tasks/<int:task_id>")
    @auth_required
    def delete_task(task_id: int):
        get_owned_task(task_id)
        get_db().execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, g.user_id))
        get_db().commit()
        return success(None, "Task deleted")

    @app.get("/api/v1/tasks/<int:task_id>/activity")
    @auth_required
    def task_activity(task_id: int):
        get_owned_task(task_id)
        rows = get_db().execute("SELECT id,action,details,created_at FROM task_activity WHERE task_id=? AND user_id=? ORDER BY created_at DESC,id DESC", (task_id, g.user_id)).fetchall()
        return success([{**dict(row), "details": json.loads(row["details"])} for row in rows])

    @app.get("/api/v1/dashboard")
    @auth_required
    def dashboard():
        today = date.today().isoformat()
        counts = get_db().execute(
            """SELECT COUNT(*) total,
               SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) pending,
               SUM(CASE WHEN status='in_progress' THEN 1 ELSE 0 END) in_progress,
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) completed,
               SUM(CASE WHEN status!='completed' AND due_date < ? THEN 1 ELSE 0 END) overdue
               FROM tasks WHERE user_id=?""",
            (today, g.user_id),
        ).fetchone()
        upcoming_until = (date.today() + timedelta(days=7)).isoformat()
        upcoming = get_db().execute(
            TASK_SELECT + " WHERE t.user_id=? AND t.status!='completed' AND t.due_date BETWEEN ? AND ? ORDER BY t.due_date ASC,t.id ASC LIMIT 10",
            (g.user_id, today, upcoming_until),
        ).fetchall()
        total = counts["total"] or 0
        completed = counts["completed"] or 0
        return success({
            "counts": {key: counts[key] or 0 for key in ("total", "pending", "in_progress", "completed", "overdue")},
            "completion_percentage": round((completed / total) * 100, 1) if total else 0.0,
            "upcoming_deadlines": [serialize_task(row) for row in upcoming],
        })

    with app.app_context():
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
        init_db()
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
