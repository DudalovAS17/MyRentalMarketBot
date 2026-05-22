from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from handlers.search.helpers_search import (build_search_prompt_keyboard, validate_search_query, build_search_results_text,
                            normalize_search_query, parse_search_page, fetch_search_page, build_search_prompt_text)
from services.item_service import ItemService

from states.search import SearchStates
from keyboards.search_kb import build_search_keyboard
from utils.functions import send_or_edit

search_router = Router()

# ───────────────────────────────────────────────── Search ─────────────────────────────────────────────────────────────
@search_router.message(Command("search"))
@search_router.message(F.text == "🔎 Поиск")
async def start_search(message: Message, state: FSMContext):
    """Запустить поиск и запросить поисковый текст."""
    await prompt_search_query(message, state)

@search_router.callback_query(F.data == "search:new_query")
async def request_new_query(callback: CallbackQuery, state: FSMContext):
    """Запросить новый поисковый текст."""
    await callback.answer()

    await prompt_search_query(callback, state)


# ────────────────────────────────────────── Запрос пользователя ───────────────────────────────────────────────────────
async def prompt_search_query(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Запросить поисковый запрос у пользователя."""

    await state.set_state(SearchStates.waiting_for_query)
    await state.update_data(search_query=None, search_page=1)

    await send_or_edit(
        event,
        build_search_prompt_text(),
        build_search_prompt_keyboard()
    )

@search_router.message(SearchStates.waiting_for_query, F.text)
async def process_search_query(message: Message, state: FSMContext, item_service: ItemService):
    """Обработать поисковый запрос пользователя."""
    query = normalize_search_query(message.text)

    validation_error = validate_search_query(query)
    if validation_error:
        await message.answer(validation_error)
        return # мы остаемся в том же состоянии FSM-состоянии

    await state.update_data(search_query=query, search_page=1)
    await state.set_state(SearchStates.browsing)

    await show_search_results(message, state, item_service, page=1)


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@search_router.callback_query(F.data.startswith("search:page:"))
async def paginate_search(callback: CallbackQuery, state: FSMContext, item_service: ItemService):
    """Показать другую страницу результатов поиска."""
    await callback.answer()

    next_page = parse_search_page(callback.data)
    if next_page is None:
        #await callback.answer("Некорректная страница.", show_alert=True)
        return

    # try:
    #     next_page = int(callback.data.split(":")[-1])
    # except (ValueError, IndexError):
    #     await prompt_search_query(callback, state)  # точно сюда?
    #     return

    data = await state.get_data()

    query = data.get("search_query")
    if not query:
        await prompt_search_query(callback, state)
        return

    await show_search_results(callback, state, item_service, page=next_page)

@search_router.callback_query(F.data == "search:back")
async def back_to_search_results(callback: CallbackQuery, state: FSMContext, item_service: ItemService):
   await callback.answer()

   await show_search_results(callback, state, item_service)


# ────────────────────────────────────── Страница результатов поиска ───────────────────────────────────────────────────
async def show_search_results(
        event: Message | CallbackQuery,
        state: FSMContext,
        item_service: ItemService,
        page: int | None = None,
) -> None:
    """Показать страницу результатов поиска."""
    data = await state.get_data()

    # запрос пользователя
    query = data.get("search_query")
    if not query:
        await prompt_search_query(event, state)
        return

    # страница
    current_page = page or data.get("search_page", 1)

    items, has_next, safe_page = await fetch_search_page(query, current_page, item_service)
    await state.update_data(search_page=safe_page)

    await send_or_edit(
        event,
        build_search_results_text(query, items, safe_page),
        build_search_keyboard(items, safe_page, has_next)
    )