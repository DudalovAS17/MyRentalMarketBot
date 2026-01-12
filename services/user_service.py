#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from typing import Optional, List

from schemas.user import UserCreate, UserUpdate, UserOut
from db.repositories.user import UserRepository
from db.models.user import User

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для работы с пользователями"""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def create(self, user_data: UserCreate) -> Optional[UserOut]:
        """Создать нового пользователя"""
        obj: Optional[User] = await self.repo.create(user_data)
        if obj:
            logger.info("Создан пользователь id=%s telegram_id=%s", obj.id, obj.telegram_id)
            return UserOut.model_validate(obj)
        return None

    async def register_user(self, user_data: UserCreate) -> Optional[UserOut]:
        """Регистрация: создаёт пользователя или обновляет, если уже есть"""
        existing = await self.repo.get_by_telegram_id(user_data.telegram_id)
        if existing:
            logger.info("Пользователь с telegram_id=%s уже существует → обновляем", user_data.telegram_id)
            updated = await self.repo.update(existing.id, UserUpdate(**user_data.model_dump()))
            # UserUpdate(**user_data.model_dump()) - мы создаём объект UserUpdate с теми же данными, что и в UserCreate
            return UserOut.model_validate(updated) if updated else None # возьмём только реально переданные поля
        """эта строчка нужна, чтобы «перелить» данные из схемы создания (UserCreate) в схему обновления (UserUpdate), 
        не вручную перечисляя каждое поле"""

        # если не найден → создаём
        obj = await self.repo.create(user_data)
        if obj:
            logger.info("Зарегистрирован новый пользователь telegram_id=%s", obj.telegram_id)
            return UserOut.model_validate(obj)
        return None

    async def get_by_id(self, user_id: int) -> Optional[UserOut]:
        """Найти пользователя по ID"""
        obj = await self.repo.get_by_id(user_id)
        return UserOut.model_validate(obj) if obj else None

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserOut]:
        """Найти пользователя по Telegram ID"""
        obj = await self.repo.get_by_telegram_id(telegram_id)
        return UserOut.model_validate(obj) if obj else None

    async def get_all(self) -> List[UserOut]:
        """Получить всех пользователей"""
        objs = await self.repo.get_all()
        return [UserOut.model_validate(o) for o in objs]

    async def update(self, user_id: int, update_data: UserUpdate) -> Optional[UserOut]:
        """Обновить данные пользователя"""
        obj = await self.repo.update(user_id, update_data)
        if obj:
            logger.info("Обновлён пользователь id=%s", obj.id)
            return UserOut.model_validate(obj)
        return None

    async def delete(self, user_id: int) -> bool:
        """Удалить пользователя"""
        success = await self.repo.delete(user_id)
        if success:
            logger.info("Удалён пользователь id=%s", user_id)
        else:
            logger.warning("Не удалось удалить пользователя id=%s", user_id)
        return success

    async def check_user_exists(self, telegram_id: int) -> bool:
        """Проверяет, существует ли пользователь с данным Telegram ID"""
        return await self.repo.exists_by_telegram_id(telegram_id)

    async def is_user_blocked(self, telegram_id: int) -> Optional[bool]:
        """Возвращает True — если пользователь заблокирован,
        False — если нет, None — если пользователь не найден"""
        user = await self.repo.get_by_telegram_id(telegram_id)
        if not user:
            logger.warning("Проверка блокировки по несуществующему пользователю: %s", telegram_id)
            return None
        return user.is_blocked
