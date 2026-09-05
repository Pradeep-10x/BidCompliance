from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str | None = None

    model_config = ConfigDict(extra="forbid")


class UserLogin(BaseModel):
    email: str
    password: str


class UserRead(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

