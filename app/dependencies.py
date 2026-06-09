"""Shared request dependencies / helpers."""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_current_user(
    request: Request, session: AsyncSession
) -> User | None:
    """Return the logged-in user from the session cookie, or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return await session.get(User, int(user_id))
