## 1. PaymentStatus 
_Понадобится, если добавишь Telegram Stars / ЮKassa_

- `PENDING`
- `PAID`
- `FAILED`
- `REFUNDED`
- `CANCELLED`

## 2. DeliveryStatus

>Пока доставка — просто поле в заявке:
>- `delivery_needed`
>- `delivery_address`
>
>Отдельный статус доставки не нужен.

_Понадобится, если будет отдельный процесс доставки_

- `NOT_REQUIRED`
- `REQUESTED`
- `SCHEDULED`
- `IN_DELIVERY`
- `DELIVERED`
- `RETURNED`

## 3. CartStatus

_Понадобится, если будет_

`cart_items` → `rental_items` → одна заявка из нескольких товаров

## 4. NotificationStatus
_Пригодиться позже, если ты будешь логировать отправку уведомлений_

- `PENDING`
- `SENT`
- `FAILED`
- `RETRYING`