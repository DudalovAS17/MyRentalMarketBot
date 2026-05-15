
# =========================================== ОТЗЫВЫ =================================================
"""Базовые инварианты (очень важно)
1) Отзыв всегда привязан к сделке (rental)
2) Один пользователь → один отзыв в рамках одной сделки
3) Отзыв можно оставить только после завершения аренды
4) Рецензент и получатель — разные пользователи
5) Рейтинг строго 1–5
6) Отзыв нельзя изменить после публикации (можно расширить потом)


@rental_router.callback_query(F.data.startswith("rental_action:review:"))
async def start_review_process(
    callback: CallbackQuery,
    state: FSMContext,
    review_service: ReviewService,
    rental_service: RentalService,
    user,
):
    await callback.answer()

    rental_id = int(callback.data.split(":")[1])

    try:
        rental = await rental_service.get_by_id(rental_id)
        if not rental:
            await callback.message.answer("❌ Сделка не найдена")
            return

        # сервис сам проверит:
        # - сделка завершена
        # - пользователь участник
        # - отзыв ещё не оставлен

        # определяем роли
        if user.id == rental.renter_id:
            reviewee_id = rental.owner_id # "reviewer_role" - собственник
        elif user.id == rental.owner_id:
            reviewee_id = rental.renter_id # "reviewer_role" - покупатель
        else:
            await callback.message.answer("❌ Вы не участник этой сделки")
            return

        await state.update_data(
            rental_id=rental_id,
            reviewer_id=user.id,
            reviewee_id=reviewee_id,
        )

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="⭐"),
                    KeyboardButton(text="⭐⭐"),
                    KeyboardButton(text="⭐⭐⭐"),
                    KeyboardButton(text="⭐⭐⭐⭐"),
                    KeyboardButton(text="⭐⭐⭐⭐⭐"),
                ],
                [KeyboardButton(text="❌ Отмена")],
            ],
            resize_keyboard=True,
        )

        text = "📊 *Оставить отзыв*\n\n Оцените опыт аренды по шкале от 1 до 5 звезд:"
        await callback.message.answer(
            text=text,
            reply_markup=keyboard,
        )

        await state.set_state(ReviewStates.rating)

    except Exception as e:
        await callback.message.answer(str(e))

# Обработка выбора рейтинга
@rental_router.callback_query(ReviewStates.rating, F.data.startswith("review_rating:"))
async def process_review_rating(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    rating = int(callback.data.split(":")[1])

    data = await state.get_data()
    review_context = data["review_context"]

    review_context["rating"] = rating
    await state.update_data(review_context=review_context)

    await state.set_state(ReviewStates.comment)

    await callback.message.edit_text(
        f"⭐ Оценка: <b>{rating}</b>\n\n"
        "💬 Напишите комментарий или нажмите «Пропустить».",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Пропустить", callback_data="review_skip_comment")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="review_cancel")],
            ]
        ),
        parse_mode="HTML",
    )

# Пропуск комментария
@rental_router.callback_query(ReviewStates.comment, F.data == "review_skip_comment")
async def skip_review_comment(
    callback: CallbackQuery,
    state: FSMContext,
    review_service: ReviewService,
):
    await callback.answer()

    data = await state.get_data()
    ctx = data["review_context"]

    try:
        await review_service.create_review(
            ReviewCreate(
                rental_id=ctx["rental_id"],
                reviewer_id=ctx["reviewer_id"],
                reviewee_id=ctx["reviewee_id"],
                rating=ctx["rating"],
                comment=None,
            )
        )
    except Exception as e:
        await callback.message.answer(f"❌ {e}")
        return

    await state.clear()

    await callback.message.edit_text(
        "✅ <b>Отзыв сохранён</b>\n\nСпасибо за ваш отзыв!",
        parse_mode="HTML",
    )

# Отмена
@rental_router.callback_query(F.data == "review_cancel")
async def cancel_review(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()
    await state.clear()

    await callback.message.edit_text(
        "❌ Оставление отзыва отменено.",
        parse_mode="HTML",
    )

"""