import asyncio
import sys
from pathlib import Path

import asyncpg

from lib.core.config import settings


MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"


async def get_connection() -> asyncpg.Connection:
    # Convert SQLAlchemy URL to asyncpg format
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(db_url)


async def ensure_migrations_table(conn: asyncpg.Connection) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            name VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)


async def get_applied_migrations(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch("SELECT name FROM _migrations")
    return {row["name"] for row in rows}


async def apply_migration(conn: asyncpg.Connection, migration_path: Path) -> None:
    migration_name = migration_path.name
    sql = migration_path.read_text()

    async with conn.transaction():
        await conn.execute(sql)
        await conn.execute(
            "INSERT INTO _migrations (name) VALUES ($1)",
            migration_name,
        )


async def main() -> None:
    print("Connecting to database...")
    conn = await get_connection()

    try:
        await ensure_migrations_table(conn)
        applied = await get_applied_migrations(conn)

        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        if not migration_files:
            print("No migration files found.")
            return

        pending = [f for f in migration_files if f.name not in applied]

        if not pending:
            print("All migrations already applied.")
            return

        for migration_path in pending:
            print(f"Applying: {migration_path.name}...")
            await apply_migration(conn, migration_path)
            print(f"  Done: {migration_path.name}")

        print(f"\nApplied {len(pending)} migration(s).")

    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
