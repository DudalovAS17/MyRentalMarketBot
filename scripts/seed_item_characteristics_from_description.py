import asyncio
import re
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from config import settings  # noqa: E402


DATABASE_URL = settings.database_url


# Если True — перед вставкой удаляем старые характеристики у товаров,
# для которых удалось распарсить description.
#
# Для dev-seed это удобно.
# Если позже в админке вручную добавишь характеристики — поставь False.
WIPE_EXISTING_FOR_PARSED_ITEMS = True


CHARACTERISTIC_NAMES = [
    # ───────────── Общие параметры ─────────────
    "Вес",
    "Масса",
    "Габариты",
    "Длина",
    "Ширина",
    "Высота",
    "Диаметр",
    "Размер",
    "Размеры",

    # ───────────── Мощность / питание ─────────────
    "Мощность",
    "Напряжение",
    "Напряжение питания",
    "Потребляемая мощность",
    "Выходная мощность",
    "Номинальная мощность",
    "Максимальная мощность",
    "Частота",
    "Ток",
    "Сила тока",

    # ───────────── Двигатель / топливо ─────────────
    "Двигатель",
    "Тип двигателя",
    "Модель двигателя",
    "Топливо",
    "Тип топлива",
    "Расход топлива",
    "Объем бака",
    "Объём бака",
    "Емкость бака",
    "Ёмкость бака",
    "Запуск",
    "Стартер",

    # ───────────── Виброплиты / трамбовки / бетон ─────────────
    "Глубина уплотнения",
    "Сила удара",
    "Центробежная сила",
    "Частота вибрации",
    "Частота ударов",
    "Размер плиты",
    "Ширина плиты",
    "Длина плиты",
    "Производительность",

    # ───────────── Резка / пилы / диски ─────────────
    "Глубина пропила",
    "Диаметр диска",
    "Посадочный диаметр",
    "Максимальная глубина реза",
    "Макс. глубина реза",
    "Глубина реза",
    "Скорость вращения",
    "Обороты",
    "Число оборотов",
    "Длина шины",
    "Шаг цепи",

    # ───────────── Буры / сверление / алмазное бурение ─────────────
    "Диаметр бура",
    "Макс диаметр бура",
    "Максимальный диаметр бура",
    "Диаметр сверления",
    "Максимальный диаметр сверления",
    "Макс. диаметр сверления",
    "Глубина сверления",
    "Тип патрона",
    "Патрон",
    "Энергия удара",

    # ───────────── Перфораторы / отбойные молотки ─────────────
    "Сила удара",
    "Энергия удара",
    "Частота ударов",
    "Количество ударов",
    "Тип крепления",
    "Тип хвостовика",
    "Хвостовик",

    # ───────────── Компрессоры / насосы / мойки ─────────────
    "Давление",
    "Рабочее давление",
    "Максимальное давление",
    "Макс. давление",
    "Производительность",
    "Подача",
    "Расход воздуха",
    "Объем ресивера",
    "Объём ресивера",
    "Емкость ресивера",
    "Ёмкость ресивера",
    "Диаметр патрубка",
    "Высота подъема",
    "Высота подъёма",
    "Глубина погружения",
    "Напор",
    "Расход воды",

    # ───────────── Подъёмное оборудование / спецтехника ─────────────
    "Грузоподъемность",
    "Грузоподъёмность",
    "Высота подъема",
    "Высота подъёма",
    "Рабочая высота",
    "Длина стрелы",
    "Вылет стрелы",
    "Объем ковша",
    "Объём ковша",
    "Ширина ковша",
    "Глубина копания",
    "Высота разгрузки",

    # ───────────── Леса / лестницы / вышки ─────────────
    "Рабочая высота",
    "Высота площадки",
    "Размер площадки",
    "Максимальная нагрузка",
    "Макс. нагрузка",
    "Количество секций",
    "Число секций",
    "Материал",
    "Длина секции",
    "Ширина настила",

    # ───────────── Тепловые пушки / отопление ─────────────
    "Тепловая мощность",
    "Мощность нагрева",
    "Площадь обогрева",
    "Расход газа",
    "Расход дизеля",
    "Поток воздуха",
    "Воздушный поток",
    "Тип нагрева",

    # ───────────── Сварка / пайка ─────────────
    "Сварочный ток",
    "Диапазон тока",
    "Диаметр электрода",
    "Рабочая температура",
    "Температура нагрева",
    "Диаметр трубы",
    "Максимальный диаметр трубы",
    "Макс. диаметр трубы",

    # ───────────── Измерительные приборы ─────────────
    "Дальность измерения",
    "Точность",
    "Погрешность",
    "Класс точности",
    "Количество лучей",
    "Цвет луча",
    "Рабочий диапазон",

    # ───────────── Станки / обработка / шлифовка ─────────────
    "Ширина обработки",
    "Глубина обработки",
    "Диаметр обработки",
    "Скорость обработки",
    "Частота вращения",
    "Размер ленты",
    "Ширина ленты",
    "Диаметр круга",
    "Размер круга",

    # ───────────── Садовая техника ─────────────
    "Ширина скашивания",
    "Ширина стрижки",
    "Диаметр лески",
    "Режущий элемент",
    "Объем травосборника",
    "Объём травосборника",
    "Ширина культивации",
    "Глубина культивации",

    # ───────────── Прочее ─────────────
    "Комплектация",
    "Назначение",
    "Тип",
    "Модель",
    "Бренд",
]


SELECT_ITEMS_SQL = """
SELECT id, description
FROM items
WHERE description IS NOT NULL
  AND trim(description) <> ''
ORDER BY id
"""


DELETE_CHARACTERISTICS_SQL = """
DELETE FROM item_characteristics
WHERE item_id = :item_id
"""


UPSERT_CHARACTERISTIC_SQL = """
INSERT INTO item_characteristics (
    item_id,
    name,
    value,
    sort_order,
    created_at,
    updated_at
)
VALUES (
    :item_id,
    :name,
    :value,
    :sort_order,
    now(),
    now()
)
ON CONFLICT (item_id, name) DO UPDATE SET
    value = EXCLUDED.value,
    sort_order = EXCLUDED.sort_order,
    updated_at = now()
"""


def clean_text(value: str | None) -> str:
    """Очистить текст от лишних пробелов."""
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_name(value: str) -> str:
    """Нормализовать название характеристики для сравнения."""
    return clean_text(value).replace("ё", "е").casefold()


CANONICAL_NAME_BY_NORMALIZED = {
    normalize_name(name): name for name in CHARACTERISTIC_NAMES
}


def build_characteristic_pattern() -> re.Pattern:
    """Собрать regex для поиска названий характеристик."""
    escaped_names = sorted(
        (re.escape(name) for name in CHARACTERISTIC_NAMES),
        key=len,
        reverse=True,
    )

    return re.compile(
        rf"(?P<name>{'|'.join(escaped_names)})\s*[—–-]\s*",
        flags=re.IGNORECASE,
    )


CHARACTERISTIC_PATTERN = build_characteristic_pattern()


def parse_characteristics(description: str) -> list[tuple[str, str]]:
    """Извлечь характеристики из description товара.

    Пример входа:
    'Глубина уплотнения — до 200 мм Вес — 91 кг Мощность — 5,5 л.с.'

    Пример выхода:
    [
        ('Глубина уплотнения', 'до 200 мм'),
        ('Вес', '91 кг'),
        ('Мощность', '5,5 л.с.'),
    ]
    """
    description = clean_text(description)
    matches = list(CHARACTERISTIC_PATTERN.finditer(description))

    if not matches:
        return []

    result: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        raw_name = match.group("name")
        normalized_name = normalize_name(raw_name)
        name = CANONICAL_NAME_BY_NORMALIZED.get(normalized_name, clean_text(raw_name))

        value_start = match.end()
        value_end = matches[index + 1].start() if index + 1 < len(matches) else len(description)

        value = clean_text(description[value_start:value_end])
        value = value.strip(" .;,-—–")

        if not value:
            continue

        result.append((name, value))

    return result


async def main() -> None:
    engine = create_async_engine(DATABASE_URL, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    total_items = 0
    parsed_items = 0
    inserted_characteristics = 0

    async with session_factory() as session:
        async with session.begin():
            rows = (await session.execute(text(SELECT_ITEMS_SQL))).mappings().all()

            for row in rows:
                total_items += 1

                item_id = row["id"]
                description = row["description"]

                characteristics = parse_characteristics(description)

                if not characteristics:
                    continue

                parsed_items += 1

                if WIPE_EXISTING_FOR_PARSED_ITEMS:
                    await session.execute(
                        text(DELETE_CHARACTERISTICS_SQL),
                        {"item_id": item_id},
                    )

                for sort_order, (name, value) in enumerate(characteristics, start=1):
                    await session.execute(
                        text(UPSERT_CHARACTERISTIC_SQL),
                        {
                            "item_id": item_id,
                            "name": name,
                            "value": value,
                            "sort_order": sort_order,
                        },
                    )
                    inserted_characteristics += 1

    await engine.dispose()

    print("✅ Seed item characteristics done")
    print(f"   Items scanned: {total_items}")
    print(f"   Items parsed: {parsed_items}")
    print(f"   Characteristics inserted/updated: {inserted_characteristics}")


if __name__ == "__main__":
    asyncio.run(main())