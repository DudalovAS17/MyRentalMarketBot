import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).with_name("stroika_categories.json")

sys.path.append(str(BASE_DIR))

from config import settings  # noqa: E402

DATABASE_URL = settings.database_url


UPSERT_SQL = """
INSERT INTO categories (
    id,
    name,
    emoji,
    parent_id,
    slug,
    sort_order,
    is_active,
    created_at,
    updated_at
)
VALUES (
    :id,
    :name,
    :emoji,
    :parent_id,
    :slug,
    :sort_order,
    :is_active,
    now(),
    now()
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    emoji = EXCLUDED.emoji,
    parent_id = EXCLUDED.parent_id,
    slug = EXCLUDED.slug,
    sort_order = EXCLUDED.sort_order,
    is_active = EXCLUDED.is_active,
    updated_at = now()
"""


async def main() -> None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    roots = [category for category in payload if category.get("parent_id") is None]
    children = [category for category in payload if category.get("parent_id") is not None]

    engine = create_async_engine(DATABASE_URL, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            for category in roots:
                await session.execute(text(UPSERT_SQL), category)

            for category in children:
                await session.execute(text(UPSERT_SQL), category)

    await engine.dispose()
    print(f"✅ Seed done: {len(payload)} categories")


if __name__ == "__main__":
    asyncio.run(main())
