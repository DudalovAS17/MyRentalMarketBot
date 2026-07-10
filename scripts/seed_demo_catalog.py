"""Seed the MVP demo catalog in the required order.

Run from repository root after migrations:
    python scripts/seed_demo_catalog.py
"""

from __future__ import annotations

import asyncio

from scripts import seed_item_characteristics_from_description
from scripts import seed_stroika_categories
from scripts import seed_stroika_items


async def main() -> None:
    """Load demo categories, items/photos, and derived item characteristics."""
    await seed_stroika_categories.main()
    await seed_stroika_items.main()
    await seed_item_characteristics_from_description.main()
    print("✅ Demo catalog seed completed")


if __name__ == "__main__":
    asyncio.run(main())