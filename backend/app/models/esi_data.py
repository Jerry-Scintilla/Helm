from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CharacterWallet(Base):
    __tablename__ = "character_wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    character: Mapped["Character"] = relationship("Character", back_populates="wallet")


class CharacterSkill(Base):
    __tablename__ = "character_skills"
    __table_args__ = (UniqueConstraint("character_id", "skill_id", name="uq_character_skill"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    skill_id: Mapped[int] = mapped_column(Integer, nullable=False)
    trained_skill_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skillpoints_in_skill: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    character: Mapped["Character"] = relationship("Character", back_populates="skills")


class CharacterAsset(Base):
    __tablename__ = "character_assets"
    __table_args__ = (UniqueConstraint("character_id", "item_id", name="uq_character_asset"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type_id: Mapped[int] = mapped_column(Integer, nullable=False)
    location_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_singleton: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    character: Mapped["Character"] = relationship("Character", back_populates="assets")


class CharacterMail(Base):
    __tablename__ = "character_mails"
    __table_args__ = (UniqueConstraint("character_id", "mail_id", name="uq_character_mail"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    mail_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    subject: Mapped[str] = mapped_column(Text, default="", nullable=False)
    from_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    character: Mapped["Character"] = relationship("Character", back_populates="mails")


from app.models.character import Character  # noqa: E402, F401
