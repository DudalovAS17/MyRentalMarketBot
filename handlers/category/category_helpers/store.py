from aiogram.fsm.context import FSMContext

async def store_selected_category(state: FSMContext, category) -> None:
    """Сохранить выбранную категорию в FSM и сбросить вложенный контекст"""
    await state.update_data(
        selected_category_id=category.id,
        selected_category_name=category.name,
        selected_subcategory_id=None,
        selected_subcategory_name=None,
        selected_item_id=None,
    )

async def store_selected_subcategory(state: FSMContext, subcategory) -> None:
    """Сохранить выбранную подкатегорию в FSM и сбросить выбранное объявление"""
    await state.update_data(
        selected_subcategory_id=subcategory.id,
        selected_subcategory_name=subcategory.name,
        selected_item_id=None,
    )

async def store_selected_item(state: FSMContext, item_id: int) -> None:
    """Сохранить выбранное объявление в FSM"""
    await state.update_data(selected_item_id=item_id)