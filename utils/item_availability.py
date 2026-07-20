# Выкинули логику:
# if has_open_rental:
#     return f"⛔ Сейчас занято (до {busy_until})" if busy_until else "⛔ Сейчас занято"

#can_request_item(item:,has_open_rental)
#item_unavailable_text(item, has_open_rental, busy_until)


# from schemas.rental import RentalOut
#
# def busy_until_text(open_rental: RentalOut | None) -> str | None:
#     """Вернуть дату окончания открытой заявки в формате dd.mm.YYYY"""
#     if open_rental is None or open_rental.end_date is None:
#         return None
#     return open_rental.end_date.strftime("%d.%m.%Y")