import asyncio
import mimetypes
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
from aiogram import Bot
from aiogram.types import FSInputFile
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


BASE_DIR = Path(__file__).resolve().parents[1]
PHOTOS_DIR = BASE_DIR / "storage" / "imported_photos"

sys.path.append(str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")

from config import settings  # noqa: E402


DATABASE_URL = settings.database_url
BOT_TOKEN = settings.token_value


UPLOAD_CHAT_ID = os.getenv("SEED_UPLOAD_CHAT_ID")

if not UPLOAD_CHAT_ID:
    raise RuntimeError(
        "SEED_UPLOAD_CHAT_ID is not set. "
        "Добавь в .env свой Telegram ID: SEED_UPLOAD_CHAT_ID=123456789"
    )


SELECT_PHOTOS_SQL = """
SELECT
    p.id,
    p.item_id,
    p.url,
    p.telegram_file_id,
    i.title
FROM photos p
JOIN items i ON i.id = p.item_id
WHERE p.url IS NOT NULL
  AND trim(p.url) <> ''
  AND p.telegram_file_id IS NULL
ORDER BY p.item_id, p.sort_order, p.id
"""


UPDATE_PHOTO_FILE_ID_SQL = """
UPDATE photos
SET
    telegram_file_id = :telegram_file_id,
    updated_at = now()
WHERE id = :photo_id
"""


def slugify_filename(value: str) -> str:
    """Сделать безопасное имя файла."""
    value = value.lower().replace("ё", "е")
    value = re.sub(r"[^a-zа-я0-9]+", "_", value, flags=re.IGNORECASE)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:80] or "photo"


def get_extension_from_url_or_content_type(url: str, content_type: str | None) -> str:
    """Определить расширение файла."""
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()

    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix

    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed in {".jpg", ".jpeg", ".png", ".webp"}:
            return guessed

    return ".jpg"


async def download_photo(
    client: httpx.AsyncClient,
    url: str,
    item_id: int,
    title: str,
) -> Path | None:
    """Скачать фото товара локально."""
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"⚠️ Download failed: item_id={item_id}, url={url}, error={exc}")
        return None

    content_type = response.headers.get("content-type", "")

    if not content_type.startswith("image/"):
        print(f"⚠️ Not an image: item_id={item_id}, content_type={content_type}, url={url}")
        return None

    extension = get_extension_from_url_or_content_type(url, content_type)

    item_dir = PHOTOS_DIR / str(item_id)
    item_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{item_id}_{slugify_filename(title)}{extension}"
    file_path = item_dir / filename

    file_path.write_bytes(response.content)

    return file_path


async def upload_photo_to_telegram(bot: Bot, file_path: Path) -> str:
    """Загрузить фото в Telegram и вернуть file_id."""
    message = await bot.send_photo(
        chat_id=int(UPLOAD_CHAT_ID),
        photo=FSInputFile(file_path),
        caption="seed photo upload",
    )

    if not message.photo:
        raise RuntimeError(f"Telegram did not return photo sizes for {file_path}")

    return message.photo[-1].file_id


async def main() -> None:
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(DATABASE_URL, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    bot = Bot(token=BOT_TOKEN)

    total = 0
    downloaded = 0
    uploaded = 0
    skipped = 0

    file_id_by_url: dict[str, str] = {}

    async with httpx.AsyncClient(
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
    ) as client:
        async with session_factory() as session:
            rows = (await session.execute(text(SELECT_PHOTOS_SQL))).mappings().all()

            print(f"Found photos to process: {len(rows)}")

            for row in rows:
                total += 1

                photo_id = row["id"]
                item_id = row["item_id"]
                url = row["url"]
                title = row["title"]

                if url in file_id_by_url:
                    telegram_file_id = file_id_by_url[url]

                    await session.execute(
                        text(UPDATE_PHOTO_FILE_ID_SQL),
                        {
                            "photo_id": photo_id,
                            "telegram_file_id": telegram_file_id,
                        },
                    )
                    await session.commit()

                    uploaded += 1
                    print(f"✅ Reused file_id: item_id={item_id}, photo_id={photo_id}")
                    continue

                file_path = await download_photo(
                    client=client,
                    url=url,
                    item_id=item_id,
                    title=title,
                )

                if file_path is None:
                    skipped += 1
                    continue

                downloaded += 1

                try:
                    telegram_file_id = await upload_photo_to_telegram(bot, file_path)
                except Exception as exc:
                    skipped += 1
                    print(f"⚠️ Telegram upload failed: item_id={item_id}, error={exc}")
                    continue

                file_id_by_url[url] = telegram_file_id

                await session.execute(
                    text(UPDATE_PHOTO_FILE_ID_SQL),
                    {
                        "photo_id": photo_id,
                        "telegram_file_id": telegram_file_id,
                    },
                )
                await session.commit()

                uploaded += 1

                print(
                    f"✅ Uploaded: item_id={item_id}, "
                    f"photo_id={photo_id}, file={file_path.name}"
                )

                await asyncio.sleep(0.15)

    await bot.session.close()
    await engine.dispose()

    print("✅ Done")
    print(f"   Total: {total}")
    print(f"   Downloaded: {downloaded}")
    print(f"   Uploaded/updated: {uploaded}")
    print(f"   Skipped: {skipped}")
    print(f"   Local folder: {PHOTOS_DIR}")


if __name__ == "__main__":
    asyncio.run(main())