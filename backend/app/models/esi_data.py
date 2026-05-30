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


class CharacterWalletJournal(Base):
    __tablename__ = "character_wallet_journals"
    __table_args__ = (UniqueConstraint("character_id", "journal_id", name="uq_char_wallet_journal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    journal_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ref_type: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    first_party_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    second_party_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    context_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    context_id_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    character: Mapped["Character"] = relationship("Character", back_populates="wallet_journal")


class CharacterWalletTransaction(Base):
    __tablename__ = "character_wallet_transactions"
    __table_args__ = (UniqueConstraint("character_id", "transaction_id", name="uq_char_wallet_tx"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    type_id: Mapped[int] = mapped_column(Integer, nullable=False)
    location_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    client_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_buy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_personal: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    journal_ref_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    character: Mapped["Character"] = relationship("Character", back_populates="wallet_transactions")


class CharacterSkillQueue(Base):
    __tablename__ = "character_skill_queues"
    __table_args__ = (UniqueConstraint("character_id", "queue_position", name="uq_char_skill_queue_pos"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    queue_position: Mapped[int] = mapped_column(Integer, nullable=False)
    skill_id: Mapped[int] = mapped_column(Integer, nullable=False)
    finished_level: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finish_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    training_start_sp: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    level_start_sp: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    level_end_sp: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    character: Mapped["Character"] = relationship("Character", back_populates="skill_queue")


class CharacterNotification(Base):
    __tablename__ = "character_notifications"
    __table_args__ = (UniqueConstraint("character_id", "notification_id", name="uq_char_notification"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    sender_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sender_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    character: Mapped["Character"] = relationship("Character", back_populates="notifications")


class CharacterContract(Base):
    """A contract the character (or their corp) is issuer/acceptor/assignee of.

    ESI only returns contracts no older than 30 days, or any still in_progress.
    Contract *items* and *bids* are fetched lazily on detail view, not stored here.
    """
    __tablename__ = "character_contracts"
    __table_args__ = (UniqueConstraint("character_id", "contract_id", name="uq_char_contract"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="character")  # character | corporation
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    issuer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    issuer_corporation_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    assignee_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    acceptor_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    start_location_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    end_location_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    for_corporation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    availability: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    reward: Mapped[float | None] = mapped_column(Float, nullable=True)
    collateral: Mapped[float | None] = mapped_column(Float, nullable=True)
    buyout: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    days_to_complete: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_issued: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    date_expired: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_accepted: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_completed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    character: Mapped["Character"] = relationship("Character", back_populates="contracts")


class CharacterKillmail(Base):
    """Summary of a killmail the character was a victim or attacker in.

    ESI /characters/{id}/killmails/recent covers the last 90 days. The full
    killmail (attackers/items) is immutable and fetched lazily on detail view;
    only the summary needed for the list is stored here.
    """
    __tablename__ = "character_killmails"
    __table_args__ = (UniqueConstraint("character_id", "killmail_id", name="uq_char_killmail"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    killmail_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    killmail_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    is_loss: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ship_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    solar_system_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    killmail_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    attacker_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    character: Mapped["Character"] = relationship("Character", back_populates="killmails")


class PlayerStructure(Base):
    """Cache for player-owned Upwell structure names resolved via ESI."""
    __tablename__ = "player_structures"

    structure_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


from app.models.character import Character  # noqa: E402, F401
