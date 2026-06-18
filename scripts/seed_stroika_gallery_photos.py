import asyncio
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from aiogram import Bot
from aiogram.types import FSInputFile
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).with_name("stroika_items.json")
PHOTOS_DIR = BASE_DIR / "storage" / "imported_gallery_photos"

sys.path.append(str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")

from config import settings  # noqa: E402


DATABASE_URL = settings.database_url
BOT_TOKEN = settings.token_value

SEED_UPLOAD_CHAT_ID = os.getenv("SEED_UPLOAD_CHAT_ID")

if not SEED_UPLOAD_CHAT_ID:
    raise RuntimeError(
        "SEED_UPLOAD_CHAT_ID is not set. "
        "Добавь в .env свой Telegram ID: SEED_UPLOAD_CHAT_ID=123456789"
    )


# Только первые 4 категории:
# 1 — Дорожно-строительная техника
# 2 — Электро инструменты
# 3 — Генераторы
# 4 — Садовая техника
TARGET_CATEGORY_IDS = {1, 2, 3, 4}

MAX_PHOTOS_PER_ITEM = 10

# Чтобы не грузить мелкие иконки преимуществ/оплаты/доставки.
MIN_IMAGE_BYTES = 12_000


DELETE_ITEM_PHOTOS_SQL = """
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
    :telegram_file_id,
    :url,
    :sort_order,
    :is_main,
    now(),
    now()
)
"""


def clean_text(value: str | None) -> str:
    """Очистить текст от лишних пробелов."""
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_title(value: str) -> str:
    """Нормализовать название товара для сопоставления."""
    return clean_text(value).replace("ё", "е").casefold()


def slugify_filename(value: str) -> str:
    """Сделать безопасное имя файла."""
    value = value.lower().replace("ё", "е")
    value = re.sub(r"[^a-zа-я0-9]+", "_", value, flags=re.IGNORECASE)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:80] or "photo"


def split_title_and_description(card_text: str) -> tuple[str, str | None]:
    """Разделить текст карточки товара на title и характеристики."""
    text = clean_text(card_text)

    for prefix in ("Цена и качество", "Наш выбор", "Хит"):
        text = clean_text(text.replace(prefix, ""))

    markers = [
        "Глубина",
        "Диаметр",
        "Вес",
        "Мощность",
        "Расход",
        "Напряжение",
        "Производительность",
        "Высота",
        "Ширина",
        "Длина",
        "Объем",
        "Объём",
        "Давление",
        "Грузоподъемность",
        "Грузоподъёмность",
        "Сила удара",
    ]

    for marker in markers:
        if marker in text:
            title, description = text.split(marker, 1)
            return clean_text(title), clean_text(marker + description)

    return clean_text(text), None


def is_product_text(text: str) -> bool:
    """Проверить, похож ли текст ссылки на карточку товара."""
    return (
        bool(text)
        and "Аренда" not in text
        and any(marker in text for marker in ("Цена и качество", "Наш выбор", "Хит"))
    )


def build_product_url_map_from_category_page(html: str, page_url: str) -> dict[str, str]:
    """Собрать mapping title -> product_url со страницы подкатегории."""
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, str] = {}

    for link in soup.find_all("a", href=True):
        text = clean_text(link.get_text(" "))

        if not is_product_text(text):
            continue

        title, _ = split_title_and_description(text)

        if not title:
            continue

        href = link.get("href")

        if not href:
            continue

        result[normalize_title(title)] = urljoin(page_url, href)

    return result


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


def extract_first_srcset_url(srcset: str | None) -> str | None:
    """Взять первый URL из srcset."""
    if not srcset:
        return None

    first = srcset.split(",")[0].strip()

    if not first:
        return None

    return first.split(" ")[0].strip()


def looks_like_product_image(url: str) -> bool:
    """Отфильтровать служебные картинки сайта."""
    url_lower = url.lower()

    if not re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", url_lower):
        return False

    banned_parts = [
        "logo",
        "sprite",
        "icon",
        "favicon",
        "social",
        "phone",
        "mail",
        "map",
        "marker",
        "badge",
        "hit",
        "our-choice",
        "rating",
        "star",
        "delivery",
        "payment",
        "oplata",
        "dostavka",
        "discount",
        "sale",
        "skidka",
        "advantage",
        "benefit",
        "bez-zaloga",
        "no-deposit",
        "cash",
        "card",
        "percent",
    ]

    return not any(part in url_lower for part in banned_parts)


def unique_keep_order(values: list[str]) -> list[str]:
    """Убрать дубли с сохранением порядка."""
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        if value in seen:
            continue

        result.append(value)
        seen.add(value)

    return result


def product_gallery_html_segment(html: str, title: str) -> str:
    """Вырезать HTML-сегмент только вокруг галереи товара.

    На странице товара нам нужны картинки из зоны:
    h1/title -> блок галереи -> до 'Характеристики'

    Это отсекает иконки оплаты, доставки, скидок и прочую служебную графику.
    """
    normalized_html = html

    title_index = normalized_html.casefold().find(title.casefold())

    if title_index == -1:
        # fallback: начинаем с первого h1
        title_index = normalized_html.find("<h1")

    if title_index == -1:
        title_index = 0

    end_markers = [
        "Характеристики",
        "Оплата",
        "Доставка",
        "Условия аренды",
        "Отзывы",
        "Похожие товары",
        "Скидка",
        "Без залога",
    ]

    end_index = len(normalized_html)

    for marker in end_markers:
        marker_index = normalized_html.find(marker, title_index + 1)

        if marker_index != -1:
            end_index = min(end_index, marker_index)

    # Берём небольшой хвост после title.
    # Если marker не найден, не берём всю страницу, чтобы не тащить иконки футера.
    if end_index == len(normalized_html):
        end_index = min(len(normalized_html), title_index + 40_000)

    return normalized_html[title_index:end_index]


def collect_image_urls_from_segment(segment_html: str, page_url: str) -> list[str]:
    """Собрать картинки только из HTML-сегмента галереи."""
    soup = BeautifulSoup(segment_html, "html.parser")

    urls: list[str] = []

    # 1. img/source теги
    for tag in soup.find_all(["img", "source"]):
        candidates = [
            tag.get("data-src"),
            tag.get("data-original"),
            tag.get("data-lazy-src"),
            tag.get("src"),
            extract_first_srcset_url(tag.get("srcset")),
            extract_first_srcset_url(tag.get("data-srcset")),
        ]

        for candidate in candidates:
            if not candidate:
                continue

            url = urljoin(page_url, candidate)

            if looks_like_product_image(url):
                urls.append(url)

    # 2. background-image
    for tag in soup.find_all(style=True):
        style = tag.get("style") or ""
        matches = re.findall(r"url\(['\"]?(?P<url>[^'\")]+)['\"]?\)", style)

        for raw_url in matches:
            url = urljoin(page_url, raw_url)

            if looks_like_product_image(url):
                urls.append(url)

    # 3. regex fallback только по сегменту галереи
    raw_urls = re.findall(
        r"""(?P<url>[^'"()\s<>]+?\.(?:jpg|jpeg|png|webp)(?:\?[^'"()\s<>]*)?)""",
        segment_html,
        flags=re.IGNORECASE,
    )

    for raw_url in raw_urls:
        url = urljoin(page_url, raw_url)

        if looks_like_product_image(url):
            urls.append(url)

    return unique_keep_order(urls)


def make_full_image_url_if_possible(url: str) -> str:
    """Попробовать превратить thumbnail URL в более крупную версию."""
    fixed = url
    fixed = fixed.replace("/storage/.thumbs/", "/storage/")
    fixed = fixed.replace("/storage/thumbs/", "/storage/")
    fixed = fixed.replace("/thumbs/", "/")
    return fixed


def expand_thumb_candidates(urls: list[str]) -> list[str]:
    """Для thumbnail URL добавить сначала предполагаемый full-size URL, потом сам thumbnail."""
    result: list[str] = []

    for url in urls:
        if "/thumbs/" in url.lower() or "thumb" in url.lower():
            full_candidate = make_full_image_url_if_possible(url)

            if full_candidate != url:
                result.append(full_candidate)

            result.append(url)
        else:
            result.append(url)

    return unique_keep_order(result)


def collect_gallery_image_urls(html: str, page_url: str, title: str) -> list[str]:
    """Собрать только фотографии основной галереи товара.

    Берём только:
        #flick-gpic .flick-gpic-item img

    Это отсекает:
    - миниатюры 80x80;
    - иконки оплаты/доставки/скидок;
    - похожие товары;
    - служебные картинки сайта.
    """
    soup = BeautifulSoup(html, "html.parser")

    gallery = soup.select_one("#flick-gpic")

    if gallery is None:
        return []

    urls: list[str] = []

    for img in gallery.select(".flick-gpic-item img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-original")
            or img.get("data-lazy-src")
        )

        if not src:
            continue

        url = urljoin(page_url, src)

        if not looks_like_product_image(url):
            continue

        urls.append(url)

    return unique_keep_order(urls)[:MAX_PHOTOS_PER_ITEM]

async def fetch_html(client: httpx.AsyncClient, url: str) -> str | None:
    """Загрузить HTML страницы."""
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as exc:
        print(f"⚠️ Failed page: {url} — {exc}")
        return None


async def download_photo(
    client: httpx.AsyncClient,
    url: str,
    item_id: int,
    title: str,
    sort_order: int,
) -> tuple[Path, str] | None:
    """Скачать фото локально."""
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    content_type = response.headers.get("content-type", "")

    if not content_type.startswith("image/"):
        return None

    extension = get_extension_from_url_or_content_type(url, content_type)

    item_dir = PHOTOS_DIR / str(item_id)
    item_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{item_id}_{sort_order}_{slugify_filename(title)}{extension}"
    file_path = item_dir / filename

    file_path.write_bytes(response.content)

    return file_path, str(response.url)


async def upload_photo_to_telegram(bot: Bot, file_path: Path) -> str | None:
    """Загрузить фото в Telegram и вернуть file_id."""
    try:
        message = await bot.send_photo(
            chat_id=int(SEED_UPLOAD_CHAT_ID),
            photo=FSInputFile(file_path),
            caption="seed gallery photo upload",
        )
    except Exception as exc:
        print(f"⚠️ Telegram upload failed: {file_path}, error={exc}")
        return None

    if not message.photo:
        return None

    return message.photo[-1].file_id


async def resolve_product_url(
    client: httpx.AsyncClient,
    item: dict,
    source_page_cache: dict[str, dict[str, str]],
) -> str | None:
    """Получить product_url товара."""
    product_url = item.get("product_url")

    if product_url:
        return product_url

    source_url = item.get("source_url")

    if not source_url:
        return None

    if source_url not in source_page_cache:
        html = await fetch_html(client, source_url)

        if not html:
            source_page_cache[source_url] = {}
        else:
            source_page_cache[source_url] = build_product_url_map_from_category_page(
                html=html,
                page_url=source_url,
            )

    return source_page_cache[source_url].get(normalize_title(item["title"]))


async def main() -> None:
    if not DATA_PATH.exists():
        raise RuntimeError(f"File not found: {DATA_PATH}")

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    items = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    target_items = [
        item
        for item in items
        if item.get("category_id") in TARGET_CATEGORY_IDS
    ]

    print(f"Target categories: {sorted(TARGET_CATEGORY_IDS)}")
    print(f"Target items: {len(target_items)}")

    engine = create_async_engine(DATABASE_URL, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    bot = Bot(token=BOT_TOKEN)

    source_page_cache: dict[str, dict[str, str]] = {}

    total_items = 0
    skipped_items = 0
    total_photos = 0

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
            for item in target_items:
                total_items += 1

                item_id = item["id"]
                title = item["title"]

                product_url = await resolve_product_url(
                    client=client,
                    item=item,
                    source_page_cache=source_page_cache,
                )

                if not product_url:
                    skipped_items += 1
                    print(f"⚠️ No product_url: item_id={item_id}, title={title}")
                    continue

                html = await fetch_html(client, product_url)

                if not html:
                    skipped_items += 1
                    continue

                image_urls = collect_gallery_image_urls(
                    html=html,
                    page_url=product_url,
                    title=title,
                )

                if not image_urls:
                    skipped_items += 1
                    print(f"⚠️ No gallery images: item_id={item_id}, {product_url}")
                    continue

                await session.execute(
                    text(DELETE_ITEM_PHOTOS_SQL),
                    {"item_id": item_id},
                )

                inserted_for_item = 0
                tried_urls: set[str] = set()

                for image_url in image_urls:
                    if image_url in tried_urls:
                        continue

                    tried_urls.add(image_url)

                    if inserted_for_item >= MAX_PHOTOS_PER_ITEM:
                        break

                    downloaded = await download_photo(
                        client=client,
                        url=image_url,
                        item_id=item_id,
                        title=title,
                        sort_order=inserted_for_item,
                    )

                    if not downloaded:
                        continue

                    file_path, final_url = downloaded

                    telegram_file_id = await upload_photo_to_telegram(
                        bot=bot,
                        file_path=file_path,
                    )

                    if not telegram_file_id:
                        continue

                    await session.execute(
                        text(INSERT_PHOTO_SQL),
                        {
                            "item_id": item_id,
                            "telegram_file_id": telegram_file_id,
                            "url": final_url,
                            "sort_order": inserted_for_item,
                            "is_main": inserted_for_item == 0,
                        },
                    )

                    inserted_for_item += 1
                    total_photos += 1

                    await asyncio.sleep(0.12)

                await session.commit()

                if inserted_for_item == 0:
                    skipped_items += 1
                    print(f"⚠️ No valid gallery photos inserted: item_id={item_id}, title={title}")
                else:
                    print(
                        f"✅ Gallery: item_id={item_id}, "
                        f"photos={inserted_for_item}, title={title}"
                    )

                await asyncio.sleep(0.25)

    await bot.session.close()
    await engine.dispose()

    print("✅ Done")
    print(f"   Items processed: {total_items}")
    print(f"   Items skipped: {skipped_items}")
    print(f"   Photos inserted: {total_photos}")
    print(f"   Local folder: {PHOTOS_DIR}")


if __name__ == "__main__":
    asyncio.run(main())