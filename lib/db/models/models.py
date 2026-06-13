from datetime import datetime, time

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_channel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schedule_time: Mapped[time] = mapped_column(Time, default=time(9, 0))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    digest_logs: Mapped[list["DigestLog"]] = relationship(back_populates="user")
    channels: Mapped[list["UserChannel"]] = relationship(back_populates="user")
    interests: Mapped[list["DigestInterest"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.telegram_id}>"


class DigestLog(Base):
    __tablename__ = "digest_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(255), nullable=False)
    channels_count: Mapped[int] = mapped_column(Integer, default=1)
    channels: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    interests: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    items_count: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="success")  # success, error, no_content
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="digest_logs")

    def __repr__(self) -> str:
        return f"<DigestLog {self.id} for user {self.user_id}>"


class UserChannel(Base):
    __tablename__ = "user_channels"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", name="uq_user_channels_user_channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="channels")

    def __repr__(self) -> str:
        return f"<UserChannel {self.channel} for user {self.user_id}>"


class DigestInterest(Base):
    __tablename__ = "digest_interests"
    __table_args__ = (
        UniqueConstraint("user_id", "interest", name="uq_digest_interests_user_interest"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    interest: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="interests")

    def __repr__(self) -> str:
        return f"<DigestInterest {self.interest} for user {self.user_id}>"
