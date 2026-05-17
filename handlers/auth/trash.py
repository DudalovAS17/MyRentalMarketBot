
# надо еще кнопку помощи обработать

#start_registration() - убрали в auth_entry
    # FSM перейдёт в состояние PHONE_NUMBER позже (в обработчике контакта)


# УВЕДОМЛЕНИЙ
#@auth_router.callback_query(F.data == "toggle_notifications:on")
#async def toggle_notifications(callback, user, enable=True):

#@auth_router.callback_query(F.data == "toggle_notifications:off")
#async def toggle_notifications(callback, user, enable=False):

"""@registration_required
async def toggle_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #elif callback_data.startswith("toggle_notifications:")
    notif_type = callback_data.split(":")[1] if len(callback_data.split(":")) > 1 else None

    if notif_type in ["new_rentals", "messages", "reviews", "promos"]:
        # Инвертируем текущее состояние уведомления
        if "notifications" not in context.user_data:
            context.user_data["notifications"] = {}

        # Инвертируем значение (по умолчанию True, если ключа нет)
        context.user_data["notifications"][notif_type] = not context.user_data["notifications"].get(notif_type,
                                                                                                    True)

        # Сохраняем настройки в БД
        try:
            from db.all_models import update_user_notification_setting
            update_user_notification_setting(user_id, notif_type, context.user_data["notifications"][notif_type])
        except Exception as e:
            logger.error(f"Не удалось обновить настройки уведомлений: {e}")

        # Повторно показываем настройки уведомлений
        from handlers.auth import show_notification_settings
        await show_notification_settings(update, context)
        return ConversationHandler.END
"""

