from aiogram.fsm.context import FSMContext

async def store_selected_category(state: FSMContext, category) -> None:
    await state.update_data(
        selected_category_id=category.id,
        selected_category_name=category.name,
        selected_subcategory_id=None,
        selected_subcategory_name=None,
        selected_item_id=None,
    )

async def store_selected_subcategory(state: FSMContext, subcategory) -> None:
    await state.update_data(
        selected_subcategory_id=subcategory.id,
        selected_subcategory_name=subcategory.name,
        selected_item_id=None,
    )

async def store_selected_item(state: FSMContext, item_id: int) -> None:
    await state.update_data(selected_item_id=item_id)