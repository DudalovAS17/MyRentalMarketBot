

def build_admin_rental_actions(rental: RentalOut) -> list[list[InlineKeyboardButton]]:
    """Собрать действия менеджера компании по заявке."""
    buttons: list[list[InlineKeyboardButton]] = []

    if rental.status == RentalStatus.REQUESTED:
        buttons.append([
            InlineKeyboardButton(
                text="🟡 Взять в работу",
                callback_data=f"{ADMIN_TAKE_RENTAL_CB}{rental.id}",
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="✅ Подтвердить заявку",
                callback_data=f"{ADMIN_CONFIRM_RENTAL_CB}{rental.id}",
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="❌ Отклонить заявку",
                callback_data=f"{ADMIN_REJECT_RENTAL_CB}{rental.id}",
            )
        ])

    elif rental.status == RentalStatus.IN_PROGRESS:
        buttons.append([
            InlineKeyboardButton(
                text="✅ Подтвердить заявку",
                callback_data=f"{ADMIN_CONFIRM_RENTAL_CB}{rental.id}",
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="❌ Отклонить заявку",
                callback_data=f"{ADMIN_REJECT_RENTAL_CB}{rental.id}",
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="🚫 Отменить от компании",
                callback_data=f"{ADMIN_CANCEL_RENTAL_CB}{rental.id}",
            )
        ])

    elif rental.status == RentalStatus.CONFIRMED:
        buttons.append([
            InlineKeyboardButton(
                text="✅ Завершить аренду",
                callback_data=f"{ADMIN_COMPLETE_RENTAL_CB}{rental.id}",
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="🚫 Отменить от компании",
                callback_data=f"{ADMIN_CANCEL_RENTAL_CB}{rental.id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 Назад к заявкам",
            callback_data=BACK_TO_ADMIN_RENTALS_CB,
        )
    ])

    return buttons