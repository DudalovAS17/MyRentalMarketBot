import asyncio
import json
from pathlib import Path

import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

#from config import DATABASE_URL

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print("SEED DATABASE_URL =", DATABASE_URL)

DATA_PATH = Path("categories.json")

UPSERT_SQL = """
INSERT INTO categories (id, name, emoji, parent_id, created_at, updated_at)
VALUES (:id, :name, :emoji, :parent_id, now(), now())
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  emoji = EXCLUDED.emoji,
  parent_id = EXCLUDED.parent_id,
  updated_at = now()
"""

async def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    engine = create_async_engine(DATABASE_URL, future=True)
    session = async_sessionmaker(engine, expire_on_commit=False)

    # 1) сначала parent_id = NULL (верхний уровень)
    roots = [c for c in payload if c.get("parent_id") is None]
    childs = [c for c in payload if c.get("parent_id") is not None]

    async with session() as s:
        async with s.begin():
            for c in roots:
                await s.execute(text(UPSERT_SQL), c)
            for c in childs:
                await s.execute(text(UPSERT_SQL), c)

    await engine.dispose()
    print(f"✅ Seed done: {len(payload)} categories")

if __name__ == "__main__":
    asyncio.run(main())
