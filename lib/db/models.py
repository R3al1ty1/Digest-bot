from datetime import datetime, time

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Time, func
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
