# service Category
from utils.errors import ValidationError

def validate_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValidationError("Название категории не может быть пустым")
    return normalized