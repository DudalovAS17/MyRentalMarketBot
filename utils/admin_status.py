import enum

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