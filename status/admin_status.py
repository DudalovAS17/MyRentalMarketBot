import enum
from db.models.rental import RentalStatus

# Имеем ли мы право вмешиваться сейчас.
# Множество состояний, в которых сделка уже завершена по смыслу.
TERMINAL_STATUSES = {
    RentalStatus.COMPLETED,
    RentalStatus.REJECTED_BY_OWNER,
    RentalStatus.REJECTED_BY_RENTER,
    RentalStatus.CANCELLED_BY_OWNER,
    RentalStatus.CANCELLED_BY_RENTER,
    RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
    RentalStatus.CANCELLED_CONFIRMED_BY_RENTER,
}

# Что именно означает “отмена” на этом этапе
# (пока так: не добавляли статусы "Админ отменил", а используем эти, но в audit будет видно, что админ отменил)
CANCEL_STATUS_MAP = {
    RentalStatus.REQUESTED: RentalStatus.REJECTED_BY_OWNER,  # REQUESTED → REJECTED_BY_OWNER
    RentalStatus.CONFIRMED: RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
    RentalStatus.ACTIVE: RentalStatus.CANCELLED_BY_OWNER,
    RentalStatus.DISPUTED: RentalStatus.CANCELLED_BY_OWNER,
}

# допустимые исходы для "закрытия спора"
ALLOWED_TARGETS = {RentalStatus.ACTIVE, RentalStatus.COMPLETED, RentalStatus.CONFIRMED}


# поле "action_type" в модели AdminAction
class AdminActionType(str, enum.Enum): # в БД строка, в коде строгость через Enum.
    ADMIN_CANCEL_RENTAL = "ADMIN_CANCEL_RENTAL"
    RESOLVE_DISPUTE = "RESOLVE_DISPUTE"
    BAN_USER = "BAN_USER"
    UNBAN_USER = "UNBAN_USER"
    # ...добавляешь по мере появления

# поле "entity_type" в модели AdminAction
class AdminEntityType(str, enum.Enum): # в БД строка, в коде строгость через Enum.
    RENTAL = "rental"
    ITEM = "item"
    USER = "user"
    COMPLAINT = "complaint"
    SUPPORT_TICKET = "support_ticket"




