# -------------------------- Schemas: Rental, Category, Item и все -----------------------------------------------------

# Pydantic v1
class Config:
    from_attributes = True

# Теперь (Pydantic v2)
model_config = ConfigDict(from_attributes=True)
# ----------------------------------------------------------------------------------------------------------------------