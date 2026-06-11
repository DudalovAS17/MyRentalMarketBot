# Nullable-карта по моделям

## Admin

`nullable=True`
- `username`
- `full_name`
- `phone`

`nullable=False`
- `id`
- `telegram_id`
- `role`
- `is_active`
- `account_status`
- `created_at`
- `updated_at`

## AdminAction

`nullable=True`
- `admin_id`
- `note`
- `payload`

`nullable=False`
- `id`
- `admin_tg_id`
- `action_type`
- `entity_type`
- `entity_id`
- `created_at`
- `updated_at`

## Category

`nullable=True`
- `emoji`
- `parent_id`
- `slug`

`nullable=False`
- `id`
- `name`
- `sort_order`
- `is_active`
- `created_at`
- `updated_at`

## Item

`nullable=True`
- `subcategory_id`
- `description`
- `short_description`
- `price_text`
- `created_by_admin_id`
- `updated_by_admin_id`
- `moderated_at`
- `max_rental_period`

`nullable=False`
- `id`
- `category_id`
- `title`
- `price`
- `available_quantity`
- `is_featured`
- `sort_order`
- `status`
- `min_rental_period`
- `views_count`
- `orders_count`
- `created_at`
- `updated_at`

## ItemCharacteristic

`nullable=True`
- нет

`nullable=False`
- `id`
- `item_id`
- `name`
- `value`
- `sort_order`
- `created_at`
- `updated_at`

## Photo

`nullable=True`
- `telegram_file_id`
- `url`

`nullable=False`
- `id`
- `item_id`
- `sort_order`
- `is_main`
- `created_at`
- `updated_at`

> Хотя `telegram_file_id` и `url` оба nullable по колонкам, check-constraint требует, чтобы хотя бы одно из них было заполнено.

## User

`nullable=True`
- `username`
- `first_name`
- `last_name`
- `full_name`
- `phone`
- `email`
- `language_code`
- `banned_at`
- `banned_by_admin_id`
- `ban_reason`

`nullable=False`
- `id`
- `telegram_id`
- `account_status`
- `created_at`
- `updated_at`

## Rental

`nullable=True`
- `start_date`
- `end_date`
- `rental_period_text`
- `total_price`
- `final_price`
- `delivery_needed`
- `delivery_address`
- `client_name`
- `client_phone`
- `client_comment`
- `manager_comment`
- `assigned_admin_id`
- `in_progress_at`
- `processed_at`
- `closed_at`
- `confirmed_at`
- `rejected_at`
- `cancelled_at`
- `completed_at`

`nullable=False`
- `id`
- `item_id`
- `status`
- `quantity`
- `user_id`
- `created_at`
- `updated_at`

## Review

`nullable=True`
- `item_id`
- `comment`
- `admin_note`

`nullable=False`
- `id`
- `rental_id`
- `user_id`
- `rating`
- `status`
- `created_at`
- `updated_at`

## SupportTicket

`nullable=True`
- `subject`
- `item_id`
- `rental_id`
- `closed_at`
- `closed_by_admin_id`
- `admin_last_reply_at`

`nullable=False`
- `id`
- `user_id`
- `text`
- `status`
- `created_at`
- `updated_at`