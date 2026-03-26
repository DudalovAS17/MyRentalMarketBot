from aiogram.fsm.context import FSMContext
from schemas.item import ItemCreateDraft

# ─────────────────────────────────────────────────show─────────────────────────────────────────────────────────────────
async def store_selected_item(state: FSMContext, item_id: int) -> None:
    await state.update_data(selected_item_id=item_id)

# ─────────────────────────────────────────────────flow_create──────────────────────────────────────────────────────────
async def store_selected_category(state: FSMContext, category) -> None:
    await state.update_data(
        selected_category_id=category.id,
        selected_category_name=category.name,
        # при смене категории логично сбросить подкатегорию
        selected_subcategory_id=None,
        selected_subcategory_name=None,
        #selected_item_id=None,
    )

async def store_selected_subcategory(state: FSMContext, category, subcategory, draft: ItemCreateDraft) -> None:
    await state.update_data(
        selected_category_id=category.id,
        selected_category_name=category.name,
        selected_subcategory_id=subcategory.id,
        selected_subcategory_name=subcategory.name,
        new_item=draft.model_dump(),
    )

async def init_edit_item_context(state: FSMContext, item) -> None:
    await state.update_data(
        edit_item_id=item.id,
        edit_field=None,
    )