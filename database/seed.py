"""Idempotent development sample data for local use."""

from __future__ import annotations

import hashlib
import os
from datetime import date, timedelta

from .connection import Database
from .repositories import CategoryRepository, TaskRepository, UserRepository


def werkzeug_compatible_hash(password: str, iterations: int = 600_000) -> str:
    """Create a salted PBKDF2 hash accepted by Werkzeug's check_password_hash."""
    salt = os.urandom(12).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"pbkdf2:sha256:{iterations}${salt}${digest}"


def seed(database: Database, password: str = "DemoPass123!") -> dict[str, int]:
    users, categories, tasks = UserRepository(database), CategoryRepository(database), TaskRepository(database)
    existing = users.get_by_email("demo@example.com")
    if existing:
        return {"user_id": existing["id"], "created": 0}
    user = users.create("demo@example.com", werkzeug_compatible_hash(password), "Demo User")
    work = categories.create(user["id"], "Work", "#2563EB")
    personal = categories.create(user["id"], "Personal", "#16A34A")
    tasks.create(user["id"], "Review weekly priorities", category_id=work["id"], priority="high", status="in_progress", due_date=(date.today() + timedelta(days=1)).isoformat(), description="Review active work and choose the next three outcomes.")
    tasks.create(user["id"], "Book dentist appointment", category_id=personal["id"], priority="medium", due_date=(date.today() + timedelta(days=5)).isoformat())
    tasks.create(user["id"], "Set up task tracker", category_id=work["id"], priority="high", status="completed", due_date=date.today().isoformat())
    tasks.create(user["id"], "Renew library books", category_id=personal["id"], priority="low", due_date=(date.today() - timedelta(days=2)).isoformat())
    return {"user_id": user["id"], "created": 4}
