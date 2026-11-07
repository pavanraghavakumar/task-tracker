import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import ActivityRepository, CategoryRepository, Database, TaskRepository, UserRepository
from database.seed import seed


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temporary.name) / "tracker.db")
        self.assertEqual(self.database.migrate(), ["001_initial_schema.sql"])
        self.users = UserRepository(self.database)
        self.categories = CategoryRepository(self.database)
        self.tasks = TaskRepository(self.database)
        self.activity = ActivityRepository(self.database)
        self.user = self.users.create("owner@example.com", "hashed", "Owner")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_migration_is_idempotent_and_enables_constraints(self) -> None:
        self.assertEqual(self.database.migrate(), [])
        with self.database.transaction() as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertTrue({"users", "categories", "tasks", "task_activity"}.issubset(tables))

    def test_crud_filter_dashboard_and_activity(self) -> None:
        category = self.categories.create(self.user["id"], "Work", "#2563EB")
        task = self.tasks.create(
            self.user["id"], "Ship database", category_id=category["id"], priority="high", due_date="2099-01-01"
        )
        self.assertEqual(self.tasks.get(self.user["id"], task["id"])["category_name"], "Work")
        self.assertEqual(len(self.tasks.list(self.user["id"], search="database", priorities=["high"])), 1)
        completed = self.tasks.update(self.user["id"], task["id"], status="completed")
        self.assertIsNotNone(completed["completed_at"])
        self.assertEqual(self.tasks.dashboard(self.user["id"])["completed"], 1)
        self.assertEqual([entry["action"] for entry in self.activity.list_for_task(self.user["id"], task["id"])], ["completed", "created"])
        self.assertTrue(self.tasks.delete(self.user["id"], task["id"]))
        self.assertTrue(self.categories.delete(self.user["id"], category["id"]))

    def test_user_isolation_and_database_constraints(self) -> None:
        other = self.users.create("other@example.com", "hashed", "Other")
        category = self.categories.create(self.user["id"], "Private")
        with self.assertRaises(ValueError):
            self.tasks.create(other["id"], "Cannot attach", category_id=category["id"])
        with self.assertRaises(sqlite3.IntegrityError):
            self.tasks.create(self.user["id"], "Bad priority", priority="urgent")
        with self.assertRaises(sqlite3.IntegrityError):
            self.users.create("OWNER@example.com", "hashed", "Duplicate")

    def test_seed_is_idempotent_and_uses_password_hash(self) -> None:
        first = seed(self.database)
        second = seed(self.database)
        sample = self.users.get_by_email("demo@example.com")
        self.assertEqual(first["created"], 4)
        self.assertEqual(second["created"], 0)
        self.assertTrue(sample["password_hash"].startswith("pbkdf2:sha256:"))
        self.assertEqual(len(self.tasks.list(sample["id"])), 4)


if __name__ == "__main__":
    unittest.main()
