from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.db.base import Base


class AuthUser(Base):
    __tablename__ = "auth_users"

    username: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True, index=True)
