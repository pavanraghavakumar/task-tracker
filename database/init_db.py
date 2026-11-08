"""Command-line database initializer: python -m database.init_db [path] [--seed]."""

from __future__ import annotations

import argparse

from .connection import Database
from .seed import seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the Personal Task Tracker SQLite database")
    parser.add_argument("path", nargs="?", default="instance/task_tracker.db")
    parser.add_argument("--seed", action="store_true", help="add idempotent local sample data")
    args = parser.parse_args()
    database = Database(args.path)
    applied = database.migrate()
    print(f"Database ready at {database.path}; migrations applied: {', '.join(applied) or 'none'}")
    if args.seed:
        result = seed(database)
        print(f"Sample user id {result['user_id']}; tasks created: {result['created']}")


if __name__ == "__main__":
    main()
