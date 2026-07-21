from typing import Optional

from sqlalchemy import select

from db.models.item_prices import ItemPriceTier
from db.repositories.base import BaseRepository
from schemas.item import ItemPriceTierCreate, ItemPriceTierUpdate


class ItemPriceTierRepository(BaseRepository):
    """Репозиторий тарифов товара без бизнес-логики выбора тарифа."""

    @staticmethod
    def _apply_order(stmt):
        return stmt.order_by(ItemPriceTier.sort_order.asc(), ItemPriceTier.min_days.asc(), ItemPriceTier.id.asc())

    async def list(self, *, limit: Optional[int] = None, offset: int = 0) -> list[ItemPriceTier]:
        async with self._session() as s:
            stmt = self._apply_order(select(ItemPriceTier))
            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)
            return await self._list(s, stmt)

    async def list_by_item_id(self, item_id: int) -> list[ItemPriceTier]:
        async with self._session() as s:
            stmt = select(ItemPriceTier).where(ItemPriceTier.item_id == item_id)
            stmt = self._apply_order(stmt)
            return await self._list(s, stmt)

    async def get_by_id(self, tier_id: int) -> Optional[ItemPriceTier]:
        async with self._session() as s:
            return await s.get(ItemPriceTier, tier_id)

    async def create(self, data: ItemPriceTierCreate) -> ItemPriceTier:
        async with self._session() as s:
            obj = ItemPriceTier(**data.model_dump())
            return await self._add_commit_refresh(s, obj)

    async def update(self, tier_id: int, data: ItemPriceTierUpdate) -> Optional[ItemPriceTier]:
        async with self._session() as s:
            obj = await s.get(ItemPriceTier, tier_id)
            if obj is None:
                return None
            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(obj, field, value)
            return await self._commit_refresh(s, obj)

    async def delete(self, tier_id: int) -> bool:
        async with self._session() as s:
            obj = await s.get(ItemPriceTier, tier_id)
            if obj is None:
                return False
            return await self._delete_commit(s, obj)