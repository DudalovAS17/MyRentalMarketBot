import asyncio
import json
import re
from decimal import Decimal
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


BASE_URL = "https://stroika-arenda.ru"
START_URL = f"{BASE_URL}/arenda/vibroplity"

CATEGORIES_PATH = Path(__file__).with_name("stroika_categories.json")
OUTPUT_PATH = Path(__file__).with_name("stroika_items.json")

ITEMS_PER_SUBCATEGORY = 4


def clean_text(value: str | None) -> str:
    """Очистить текст от лишних пробелов."""
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_name(value: str) -> str:
    """Нормализовать название категории для сопоставления."""
    return clean_text(value).casefold().replace("ё", "е")


def parse_price(price_text: str) -> Decimal:
    """Извлечь числовую цену из текста."""
    match = re.search(r"(\d[\d\s]*)", price_text)
    if not match:
        return Decimal("0")

    return Decimal(match.group(1).replace(" ", ""))


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
        "Давление",
    ]

    for marker in markers:
        if marker in text:
            title, description = text.split(marker, 1)
            return clean_text(title), clean_text(marker + description)

    return clean_text(text), None


def build_menu_url_map(html: str) -> dict[str, str]:
    """Собрать реальные URL подкатегорий с сайта по тексту ссылки."""
    soup = BeautifulSoup(html, "html.parser")

    result: dict[str, str] = {}

    for link in soup.find_all("a", href=True):
        name = clean_text(link.get_text(" "))
        href = link.get("href")

        if not name or not href:
            continue

        if "/arenda/" not in href:
            continue

        full_url = urljoin(BASE_URL, href)
        result[normalize_name(name)] = full_url

    return result


def parse_product_cards(html: str, page_url: str, limit: int) -> list[dict]:
    """Распарсить товары со страницы подкатегории."""
    soup = BeautifulSoup(html, "html.parser")

    links = soup.find_all("a", href=True)
    products: list[dict] = []

    i = 0
    while i < len(links):
        link = links[i]
        text = clean_text(link.get_text(" "))

        is_product_link = (
            text
            and "Аренда" not in text
            and any(marker in text for marker in ("Цена и качество", "Наш выбор", "Хит"))
        )

        if not is_product_link:
            i += 1
            continue

        title, description = split_title_and_description(text)

        if not title:
            i += 1
            continue

        price_text = None

        # Цена обычно идёт следующей ссылкой после карточки товара.
        for j in range(i + 1, min(i + 4, len(links))):
            candidate_text = clean_text(links[j].get_text(" "))
            if "Аренда" in candidate_text and "р" in candidate_text:
                price_text = candidate_text
                break

        price = parse_price(price_text or "")

        products.append(
            {
                "title": title,
                "description": description,
                "short_description": description[:300] if description else None,
                "price": str(price),
                "price_text": price_text,
                "source_url": page_url,
                "photos": [],
            }
        )

        if len(products) >= limit:
            break

        i += 1

    return products


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
    categories = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))

    subcategories = [
        category
        for category in categories
        if category.get("parent_id") is not None
    ]

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
        start_html = await fetch_html(client, START_URL)
        if not start_html:
            raise RuntimeError("Cannot load start page")

        url_by_name = build_menu_url_map(start_html)

        result: list[dict] = []
        next_item_id = 1

        for subcategory in subcategories:
            subcategory_name = subcategory["name"]
            page_url = url_by_name.get(normalize_name(subcategory_name))

            if not page_url:
                print(f"⚠️ No source URL for: {subcategory_name}")
                continue

            html = await fetch_html(client, page_url)
            if not html:
                continue

            products = parse_product_cards(
                html=html,
                page_url=page_url,
                limit=ITEMS_PER_SUBCATEGORY,
            )

            if not products:
                print(f"⚠️ No products parsed: {page_url}")
                continue

            for sort_order, product in enumerate(products, start=1):
                result.append(
                    {
                        "id": next_item_id,
                        "category_id": subcategory["parent_id"],
                        "subcategory_id": subcategory["id"],
                        "title": product["title"],
                        "description": product["description"],
                        "short_description": product["short_description"],
                        "price": product["price"],
                        "price_text": product["price_text"],
                        "available_quantity": 1,
                        "is_featured": False,
                        "sort_order": sort_order,
                        "status": "ACTIVE",
                        "min_rental_period": 1,
                        "max_rental_period": None,
                        "views_count": 0,
                        "orders_count": 0,
                        "source_url": product["source_url"],
                        "photos": product["photos"],
                    }
                )
                next_item_id += 1

            print(f"✅ Parsed {len(products)} items: {subcategory_name}")

            await asyncio.sleep(0.25)

    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ Saved {len(result)} items to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())