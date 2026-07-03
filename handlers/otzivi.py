
# ОТЗЫВЫ

"""Базовые инварианты (очень важно)
1) Отзыв всегда привязан к сделке (rentals)
2) Один пользователь → один отзыв в рамках одной сделки
3) Отзыв можно оставить только после завершения аренды
4) Рецензент и получатель — разные пользователи
5) Рейтинг строго 1–5
6) Отзыв нельзя изменить после публикации (можно расширить потом)


@rental_router.callback_query(F.data.startswith("rental_action:review:"))
async def start_review_process()

    keyboard=[
    [
        KeyboardButton(text="⭐"),
        KeyboardButton(text="⭐⭐"),
        KeyboardButton(text="⭐⭐⭐"),
        KeyboardButton(text="⭐⭐⭐⭐"),
        KeyboardButton(text="⭐⭐⭐⭐⭐"),
    ],

    "📊 *Оставить отзыв*\n\n Оцените опыт аренды по шкале от 1 до 5 звезд:"


# Обработка выбора рейтинга
@rental_router.callback_query(ReviewStates.rating, F.data.startswith("review_rating:"))
async def process_review_rating()
        f"⭐ Оценка: <b>{rating}</b>\n\n"
        "💬 Напишите комментарий или нажмите «Пропустить».",


# Пропуск комментария
@rental_router.callback_query(ReviewStates.comment, F.data == "review_skip_comment")
async def skip_review_comment()
        "✅ <b>Отзыв сохранён</b>\n\nСпасибо за ваш отзыв!",

# Отмена
@rental_router.callback_query(F.data == "review_cancel")
async def cancel_review()
        "❌ Оставление отзыва отменено."

"""