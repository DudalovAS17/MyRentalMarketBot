from decimal import Decimal
from typing import Optional

def ui_str(value: Optional[str], default: str = "-") -> str:
    return value if value else default

def ui_money(value: Optional[Decimal], default: str = "0") -> str:
    return str(value) if value is not None else default

def ui_int(value: Optional[int], default: int = 0) -> int:
    return value if value is not None else default

# Красивое имя вида: "Александр С. (@potch)"
def fmt_person(name: str, username: str = None) -> str:
    return f"{name} (@{username})" if username else name