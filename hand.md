## 1.


Служебные разделы - сюда будет доступ не по текстам, а только через кнопки:
- "⚙️ Настройки": lambda: show_settings(state),
- "📊 Статистика": lambda: show_statistics(state),
- "🏆 Достижения": lambda: show_achievements(state),

-  "📦 Сдать в аренду": lambda: start_create_item_from_menu(message, state, user),
- "📦 Мои объявления": lambda: show_my_items(message, item_service, user),

- "📱 Изменить номер": lambda: request_phone_number_change(message, state),

🔔 Уведомления — отдельная ветка (не FSM)
```
if text.startswith("🔔 Уведомления"):
    #return lambda: show_notification_settings(message, state)
```







@dataclass
    - автоматически создаёт __init__
    - хранит данные как у обычного объекта
    - делает код читаемым и явным
dataclass = удобная форма записи структуры данных.