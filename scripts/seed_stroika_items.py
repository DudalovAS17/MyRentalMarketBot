import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).with_name("stroika_items.json")

sys.path.append(str(BASE_DIR))

from config import settings  # noqa: E402


DATABASE_URL = settings.database_url


UPSERT_ITEM_SQL = """
INSERT INTO items (
    id,
    category_id,
    subcategory_id,
    title,
    description,
    short_description,
    price,
    price_text,
    available_quantity,
    is_featured,
    sort_order,
    status,
    min_rental_period,
    max_rental_period,
    views_count,
    orders_count,
    created_at,
    updated_at
)
VALUES (
    :id,
    :category_id,
    :subcategory_id,
    :title,
    :description,
    :short_description,
    :price,
    :price_text,
    :available_quantity,
    :is_featured,
    :sort_order,
    :status,
    :min_rental_period,
    :max_rental_period,
    :views_count,
    :orders_count,
    now(),
    now()
)
ON CONFLICT (id) DO UPDATE SET
    category_id = EXCLUDED.category_id,
    subcategory_id = EXCLUDED.subcategory_id,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    short_description = EXCLUDED.short_description,
    price = EXCLUDED.price,
    price_text = EXCLUDED.price_text,
    available_quantity = EXCLUDED.available_quantity,
    is_featured = EXCLUDED.is_featured,
    sort_order = EXCLUDED.sort_order,
    status = EXCLUDED.status,
    min_rental_period = EXCLUDED.min_rental_period,
    max_rental_period = EXCLUDED.max_rental_period,
    views_count = EXCLUDED.views_count,
    orders_count = EXCLUDED.orders_count,
    updated_at = now()
"""


DELETE_PHOTOS_SQL = """
DELETE FROM photos
WHERE item_id = :item_id
"""


INSERT_PHOTO_SQL = """
INSERT INTO photos (
    item_id,
    telegram_file_id,
    url,
    sort_order,
    is_main,
    created_at,
    updated_at
)
VALUES (
    :item_id,
    NULL,
    :url,
    :sort_order,
    :is_main,
    now(),
    now()
)
"""


async def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    engine = create_async_engine(DATABASE_URL, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            for item in payload:
                photos = item.pop("photos", [])

                await session.execute(text(UPSERT_ITEM_SQL), item)

                await session.execute(
                    text(DELETE_PHOTOS_SQL),
                    {"item_id": item["id"]},
                )

                for photo in photos:
                    if not photo.get("url"):
                        continue

                    await session.execute(
                        text(INSERT_PHOTO_SQL),
                        {
                            "item_id": item["id"],
                            "url": photo["url"],
                            "sort_order": photo.get("sort_order", 0),
                            "is_main": photo.get("is_main", False),
                        },
                    )

    await engine.dispose()
    print(f"✅ Seed done: {len(payload)} items")


if __name__ == "__main__":
    asyncio.run(main())