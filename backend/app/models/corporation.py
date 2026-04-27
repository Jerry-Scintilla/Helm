from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Corporation(Base):
    __tablename__ = "corporations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corporation_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ceo_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    alliance_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    members: Mapped[list["CorporationMember"]] = relationship("CorporationMember", back_populates="corporation", cascade="all, delete-orphan")
    wallets: Mapped[list["CorporationWallet"]] = relationship("CorporationWallet", back_populates="corporation", cascade="all, delete-orphan")
    wallet_journals: Mapped[list["CorporationWalletJournal"]] = relationship("CorporationWalletJournal", back_populates="corporation", cascade="all, delete-orphan")
    assets: Mapped[list["CorporationAsset"]] = relationship("CorporationAsset", back_populates="corporation", cascade="all, delete-orphan")


class CorporationMember(Base):
    __tablename__ = "corporation_members"
    __table_args__ = (UniqueConstraint("corporation_id", "character_id", name="uq_corp_member"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corporation_id: Mapped[int] = mapped_column(Integer, ForeignKey("corporations.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ship_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ship_type_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    logon_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    logoff_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    corporation: Mapped["Corporation"] = relationship("Corporation", back_populates="members")


class CorporationWallet(Base):
    __tablename__ = "corporation_wallets"
    __table_args__ = (UniqueConstraint("corporation_id", "wallet_division", name="uq_corp_wallet_div"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corporation_id: Mapped[int] = mapped_column(Integer, ForeignKey("corporations.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_division: Mapped[int] = mapped_column(Integer, nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    corporation: Mapped["Corporation"] = relationship("Corporation", back_populates="wallets")


class CorporationWalletJournal(Base):
    __tablename__ = "corporation_wallet_journals"
    __table_args__ = (UniqueConstraint("corporation_id", "division", "journal_id", name="uq_corp_wallet_journal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corporation_id: Mapped[int] = mapped_column(Integer, ForeignKey("corporations.id", ondelete="CASCADE"), nullable=False, index=True)
    division: Mapped[int] = mapped_column(Integer, nullable=False)
    journal_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ref_type: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    first_party_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    second_party_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    corporation: Mapped["Corporation"] = relationship("Corporation", back_populates="wallet_journals")


class CorporationAsset(Base):
    __tablename__ = "corporation_assets"
    __table_args__ = (UniqueConstraint("corporation_id", "item_id", name="uq_corp_asset"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corporation_id: Mapped[int] = mapped_column(Integer, ForeignKey("corporations.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type_id: Mapped[int] = mapped_column(Integer, nullable=False)
    location_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_singleton: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    corporation: Mapped["Corporation"] = relationship("Corporation", back_populates="assets")
