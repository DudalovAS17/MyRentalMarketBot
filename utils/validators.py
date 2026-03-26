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