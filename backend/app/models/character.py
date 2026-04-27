from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    character_name: Mapped[str] = mapped_column(String(256), nullable=False)
    corporation_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    alliance_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Stored encrypted at rest; rotation handled separately
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship("User", back_populates="characters")
    wallet: Mapped["CharacterWallet | None"] = relationship("CharacterWallet", back_populates="character", uselist=False, cascade="all, delete-orphan")
    skills: Mapped[list["CharacterSkill"]] = relationship("CharacterSkill", back_populates="character", cascade="all, delete-orphan")
    assets: Mapped[list["CharacterAsset"]] = relationship("CharacterAsset", back_populates="character", cascade="all, delete-orphan")
    mails: Mapped[list["CharacterMail"]] = relationship("CharacterMail", back_populates="character", cascade="all, delete-orphan")


from app.models.user import User  # noqa: E402, F401
from app.models.esi_data import CharacterWallet, CharacterSkill, CharacterAsset, CharacterMail  # noqa: E402, F401
