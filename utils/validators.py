# service Category
from utils.errors import ValidationError

def validate_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValidationError("Название категории не может быть пустым")
    return normalized


def parse_callback(data: str | None, prefix: str) -> int | None: # _parse_callback_entity_id
    if not data or not data.startswith(prefix):
        return None

    raw_value = data[len(prefix):] # data.split(":")[1]
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


""" parse_callback(data, prefix) как раз умеет:
- проверить prefix;
- отрезать prefix;
- преобразовать остаток в int;
- вернуть None, если что-то не так.


    Это:
        try:
            rental_id = int(callback.data.split(":")[1]) # split(":", 1)
        except (IndexError, ValueError):
            await callback.answer("Некорректная сделка.", show_alert=True)
            return
        
    реализуется через:    
        rental_id = parse_callback(callback.data, RENTAL_DETAILS_CB)
            if rental_id is None:
                await callback.answer("Некорректная сделка.", show_alert=True)
                return
"""