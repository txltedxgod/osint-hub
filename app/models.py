"""SQLAlchemy ORM models (async, SQLite)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    salt: Mapped[str] = mapped_column(String(64))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    searches: Mapped[list[Search]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Search.created_at.desc()",
    )


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    query: Mapped[str] = mapped_column(String(128), index=True)
    tools: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="completed")
    total_found: Mapped[int] = mapped_column(Integer, default=0)
    sites_checked: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    user: Mapped[User] = relationship(back_populates="searches")
    results: Mapped[list[Result]] = relationship(
        back_populates="search",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Result.site_name",
    )

    @property
    def tool_list(self) -> list[str]:
        return [t for t in self.tools.split(",") if t]


class Result(Base):
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(primary_key=True)
    search_id: Mapped[int] = mapped_column(
        ForeignKey("searches.id", ondelete="CASCADE"), index=True
    )
    tool: Mapped[str] = mapped_column(String(32))
    site_name: Mapped[str] = mapped_column(String(128))
    url: Mapped[str] = mapped_column(Text, default="")

    search: Mapped[Search] = relationship(back_populates="results")
