"""Connection lifecycle and migration support using only Python's standard library."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Database:
    """Creates configured SQLite connections and applies ordered SQL migrations."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def migrate(self, migrations_dir: str | Path | None = None) -> list[str]:
        directory = Path(migrations_dir) if migrations_dir else Path(__file__).with_name("migrations")
        applied: list[str] = []
        with self.transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT "
                "(strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))"
            )
            existing = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
            for migration in sorted(directory.glob("*.sql")):
                if migration.name in existing:
                    continue
                connection.executescript(migration.read_text(encoding="utf-8"))
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (migration.name,))
                applied.append(migration.name)
        return applied
