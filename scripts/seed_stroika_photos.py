import asyncio
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).with_name("stroika_items.json")

sys.path.append(str(BASE_DIR))

from config import settings  # noqa: E402


DATABASE_URL = settings.database_url


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
    NULL,
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


def split_title_and_description(card_text: str) -> tuple[str, str | None]:
    """Разделить текст карточки на название товара и характеристики."""
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


def extract_image_url_from_srcset(srcset: str | None) -> str | None:
    """Взять первый URL из srcset."""
    if not srcset:
        return None

    first_part = srcset.split(",")[0].strip()
    if not first_part:
        return None

    return first_part.split(" ")[0].strip()


def image_url_from_img(tag, page_url: str) -> str | None:
    """Достать URL картинки из img/source элемента."""
    candidate = (
        tag.get("data-src")
        or tag.get("data-original")
        or tag.get("data-lazy-src")
        or tag.get("data-srcset")
        or tag.get("src")
        or extract_image_url_from_srcset(tag.get("srcset"))
    )

    if not candidate:
        return None

    # Если data-srcset/srcset — там может быть несколько URL.
    if "," in candidate or " " in candidate:
        candidate_from_srcset = extract_image_url_from_srcset(candidate)
        if candidate_from_srcset:
            candidate = candidate_from_srcset

    return urljoin(page_url, candidate)


def image_url_from_style(style: str | None, page_url: str) -> str | None:
    """Достать URL картинки из inline style background-image."""
    if not style:
        return None

    match = re.search(r"url\(['\"]?(?P<url>[^'\")]+)['\"]?\)", style)

    if not match:
        return None

    return urljoin(page_url, match.group("url"))


def looks_like_product_image(url: str) -> bool:
    """Отфильтровать служебные иконки/логотипы от товарных фото."""
    url_lower = url.lower()

    if not re.search(r"\.(jpg|jpeg|png|webp|svg)(\?|$)", url_lower):
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
    ]

    return not any(part in url_lower for part in banned_parts)


def find_card_container(tag):
    """Подняться вверх по DOM и найти контейнер карточки товара."""
    current = tag

    for _ in range(10):
        if current is None:
            return None

        html = str(current)
        text = clean_text(current.get_text(" "))

        has_image = (
            current.find("img") is not None
            or current.find("source") is not None
            or "background-image" in html
            or re.search(r"\.(jpg|jpeg|png|webp|svg)", html, flags=re.IGNORECASE)
        )

        looks_like_product = (
            "Цена и качество" in text
            or "Аренда от" in text
            or "Аренда " in text
            or "Наш выбор" in text
            or "Хит" in text
        )

        if has_image and looks_like_product:
            return current

        current = current.parent

    return None


def extract_image_from_container(container, page_url: str) -> str | None:
    """Достать URL изображения из контейнера карточки."""
    if container is None:
        return None

    # 1. Обычные img/source
    for tag in container.find_all(["img", "source"]):
        url = image_url_from_img(tag, page_url)

        if url and looks_like_product_image(url):
            return url

    # 2. background-image в style
    for tag in container.find_all(style=True):
        url = image_url_from_style(tag.get("style"), page_url)

        if url and looks_like_product_image(url):
            return url

    # 3. regex fallback по HTML контейнера
    html = str(container)
    matches = re.findall(
        r"""(?P<url>[^'"()\s<>]+?\.(?:jpg|jpeg|png|webp|svg)(?:\?[^'"()\s<>]*)?)""",
        html,
        flags=re.IGNORECASE,
    )

    for raw_url in matches:
        url = urljoin(page_url, raw_url)

        if looks_like_product_image(url):
            return url

    return None


def parse_page_products_with_images(html: str, page_url: str) -> list[dict]:
    """Распарсить товары страницы сразу вместе с картинками."""
    soup = BeautifulSoup(html, "html.parser")

    result: list[dict] = []
    seen_titles: set[str] = set()

    for link in soup.find_all("a", href=True):
        text = clean_text(link.get_text(" "))

        if not is_product_text(text):
            continue

        title, _ = split_title_and_description(text)

        if not title:
            continue

        normalized_title = normalize_title(title)

        if normalized_title in seen_titles:
            continue

        container = find_card_container(link)
        image_url = extract_image_from_container(container, page_url)

        if not image_url:
            continue

        result.append(
            {
                "title": title,
                "image_url": image_url,
            }
        )

        seen_titles.add(normalized_title)

    return result


async def fetch_html(client: httpx.AsyncClient, url: str) -> str | None:
    """Загрузить HTML страницы."""
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as exc:
        print(f"⚠️ Failed: {url} — {exc}")
        return None


async def main() -> None:
    if not DATA_PATH.exists():
        raise RuntimeError(f"File not found: {DATA_PATH}")

    items = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    items_by_source_url: dict[str, list[dict]] = defaultdict(list)

    for item in items:
        source_url = item.get("source_url")

        if source_url:
            items_by_source_url[source_url].append(item)

    engine = create_async_engine(DATABASE_URL, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    total_inserted = 0
    total_matched = 0

    async with httpx.AsyncClient(
        timeout=20,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
    ) as client:
        async with session_factory() as session:
            async with session.begin():
                for source_url, page_items in items_by_source_url.items():
                    html = await fetch_html(client, source_url)

                    if not html:
                        continue

                    page_products = parse_page_products_with_images(html, source_url)

                    if not page_products:
                        print(f"⚠️ No products with images: {source_url}")
                        continue

                    image_by_title: dict[str, str] = {
                        normalize_title(product["title"]): product["image_url"]
                        for product in page_products
                    }

                    matched_on_page = 0

                    for item in page_items:
                        item_id = item["id"]
                        title = item["title"]

                        image_url = image_by_title.get(normalize_title(title))

                        if not image_url:
                            continue

                        await session.execute(
                            text(DELETE_ITEM_PHOTOS_SQL),
                            {"item_id": item_id},
                        )

                        await session.execute(
                            text(INSERT_PHOTO_SQL),
                            {
                                "item_id": item_id,
                                "url": image_url,
                                "sort_order": 0,
                                "is_main": True,
                            },
                        )

                        item["photos"] = [
                            {
                                "url": image_url,
                                "sort_order": 0,
                                "is_main": True,
                            }
                        ]

                        matched_on_page += 1
                        total_matched += 1
                        total_inserted += 1

                    print(
                        f"✅ Photos: {matched_on_page}/{len(page_items)} "
                        f"items — {source_url}"
                    )

                    await asyncio.sleep(0.25)

    await engine.dispose()

    DATA_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("✅ Seed photos done")
    print(f"   Matched items: {total_matched}")
    print(f"   Photos inserted: {total_inserted}")


if __name__ == "__main__":
    asyncio.run(main())