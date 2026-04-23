from __future__ import annotations

import argparse
import asyncio
import hashlib
from pathlib import Path

import asyncpg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply Mythos SQL migrations.")
    parser.add_argument("--dsn", required=True, help="Postgres DSN")
    parser.add_argument(
        "--schema",
        default="mythos",
        help="Schema containing migration tracking table",
    )
    parser.add_argument(
        "--migrations-dir",
        default="sql/migrations",
        help="Directory containing migration .sql files",
    )
    return parser.parse_args()


async def run(dsn: str, schema: str, migrations_dir: Path) -> int:
    if not migrations_dir.exists():
        print(f"migrations directory not found: {migrations_dir}")
        return 1

    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        print("no migration files found")
        return 0

    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {schema}.schema_migrations (
                filename TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

        for file_path in files:
            sql = file_path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            row = await conn.fetchrow(
                f"SELECT checksum FROM {schema}.schema_migrations WHERE filename=$1",
                file_path.name,
            )
            if row is not None:
                existing_checksum = str(row["checksum"])
                if existing_checksum != checksum:
                    raise RuntimeError(
                        f"migration checksum mismatch for {file_path.name}; "
                        "manual intervention required"
                    )
                print(f"skip {file_path.name} (already applied)")
                continue

            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    f"INSERT INTO {schema}.schema_migrations (filename, checksum) VALUES ($1, $2)",
                    file_path.name,
                    checksum,
                )
            print(f"applied {file_path.name}")
    finally:
        await conn.close()
    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(run(args.dsn, args.schema, Path(args.migrations_dir)))


if __name__ == "__main__":
    raise SystemExit(main())
