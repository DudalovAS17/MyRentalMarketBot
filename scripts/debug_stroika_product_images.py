import asyncio
import re
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


PRODUCT_URL = "https://stroika-arenda.ru/arenda/products/vibroplita-champion-pc9045f"

DEBUG_DIR = Path("debug_stroika")
DEBUG_DIR.mkdir(exist_ok=True)


def clean_text(value: str | None) -> str:
    """Очистить текст от лишних пробелов."""
    return re.sub(r"\s+", " ", value or "").strip()


def extract_first_srcset_url(srcset: str | None) -> str | None:
    """Взять первый URL из srcset."""
    if not srcset:
        return None

    first = srcset.split(",")[0].strip()

    if not first:
        return None

    return first.split(" ")[0].strip()


def collect_img_candidates(html: str, page_url: str) -> list[dict]:
    """Собрать все кандидаты картинок из HTML."""
    soup = BeautifulSoup(html, "html.parser")
    result: list[dict] = []
    seen: set[str] = set()

    for img in soup.find_all(["img", "source"]):
        candidates = [
            img.get("src"),
            img.get("data-src"),
            img.get("data-original"),
            img.get("data-lazy-src"),
            extract_first_srcset_url(img.get("srcset")),
            extract_first_srcset_url(img.get("data-srcset")),
        ]

        for candidate in candidates:
            if not candidate:
                continue

            if not re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", candidate, flags=re.IGNORECASE):
                continue

            url = urljoin(page_url, candidate)

            if url in seen:
                continue

            seen.add(url)

            parent = img.parent
            parent_classes = " ".join(parent.get("class", [])) if parent else ""
            parent_text = clean_text(parent.get_text(" ")) if parent else ""

            result.append(
                {
                    "url": url,
                    "tag": img.name,
                    "alt": img.get("alt"),
                    "class": " ".join(img.get("class", [])),
                    "parent_class": parent_classes,
                    "parent_text": parent_text[:200],
                    "html": str(parent)[:600] if parent else str(img)[:600],
                }
            )

    # fallback: любые ссылки на картинки в HTML
    raw_urls = re.findall(
        r"""(?P<url>[^'"()\s<>]+?\.(?:jpg|jpeg|png|webp)(?:\?[^'"()\s<>]*)?)""",
        html,
        flags=re.IGNORECASE,
    )

    for raw_url in raw_urls:
        url = urljoin(page_url, raw_url)

        if url in seen:
            continue

        seen.add(url)

        result.append(
            {
                "url": url,
                "tag": "regex",
                "alt": None,
                "class": "",
                "parent_class": "",
                "parent_text": "",
                "html": "",
            }
        )

    return result


async def get_image_info(client: httpx.AsyncClient, url: str) -> dict:
    """Получить размер и content-type картинки."""
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

        return {
            "ok": True,
            "final_url": str(response.url),
            "content_type": response.headers.get("content-type"),
            "bytes": len(response.content),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": repr(exc),
        }


async def main() -> None:
    timeout = httpx.Timeout(20.0, connect=10.0)

    async with httpx.AsyncClient(
        timeout=timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
    ) as client:
        response = await client.get(PRODUCT_URL, follow_redirects=True)
        response.raise_for_status()

        html = response.text

        html_path = DEBUG_DIR / "product_page.html"
        html_path.write_text(html, encoding="utf-8")

        candidates = collect_img_candidates(html, PRODUCT_URL)

        print(f"HTML saved to: {html_path.resolve()}")
        print(f"Candidates found: {len(candidates)}")
        print()

        report_lines: list[str] = []

        for index, candidate in enumerate(candidates, start=1):
            info = await get_image_info(client, candidate["url"])

            block = [
                f"#{index}",
                f"URL: {candidate['url']}",
                f"TAG: {candidate['tag']}",
                f"ALT: {candidate['alt']}",
                f"CLASS: {candidate['class']}",
                f"PARENT_CLASS: {candidate['parent_class']}",
                f"PARENT_TEXT: {candidate['parent_text']}",
                f"INFO: {info}",
                f"HTML: {candidate['html']}",
                "-" * 100,
            ]

            text = "\n".join(block)
            print(text)
            report_lines.append(text)

        report_path = DEBUG_DIR / "images_report.txt"
        report_path.write_text("\n\n".join(report_lines), encoding="utf-8")

        print()
        print(f"Report saved to: {report_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())