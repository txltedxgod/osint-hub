"""Orchestrates an OSINT search and persists it to the database."""
from __future__ import annotations

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Result, Search, User
from app.services import osint

logger = logging.getLogger("osint_hub.search")

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{2,64}$")


class SearchError(Exception):
    """Raised when a search request is invalid."""


def validate_username(raw: str) -> str:
    username = (raw or "").strip()
    if not _USERNAME_RE.match(username):
        raise SearchError(
            "Username must be 2-64 characters: letters, digits, '.', '_' or '-'."
        )
    return username


def validate_tools(raw_tools: list[str]) -> list[str]:
    allowed = {"sherlock", "maigret"}
    tools = [t for t in raw_tools if t in allowed]
    if not tools:
        raise SearchError("Select at least one engine (Sherlock or Maigret).")
    # keep a stable order
    return [t for t in ("sherlock", "maigret") if t in tools]


async def perform_search(
    session: AsyncSession, user: User, raw_username: str, raw_tools: list[str]
) -> Search:
    username = validate_username(raw_username)
    tools = validate_tools(raw_tools)

    runs = await osint.run_engines(username, tools)

    search = Search(
        user_id=user.id,
        query=username,
        tools=",".join(tools),
        status="completed",
    )

    total = 0
    used_tools: list[str] = []
    for run in runs:
        if run.available:
            used_tools.append(run.tool)
        for hit in run.hits:
            search.results.append(
                Result(tool=hit.tool, site_name=hit.site_name, url=hit.url)
            )
            total += 1

    search.total_found = total
    search.sites_checked = len(search.results)
    if not used_tools:
        search.status = "engines_unavailable"
    elif len(used_tools) < len(tools):
        search.status = "partial"

    session.add(search)
    await session.commit()
    await session.refresh(search)
    logger.info(
        "User %s searched '%s' (%s) -> %d accounts",
        user.username,
        username,
        ",".join(tools),
        total,
    )
    return search


async def get_search(
    session: AsyncSession, search_id: int, user: User
) -> Search | None:
    search = await session.get(Search, search_id)
    if search is None:
        return None
    if search.user_id != user.id and not user.is_admin:
        return None
    return search


async def list_searches(session: AsyncSession, user: User, limit: int = 100):
    stmt = (
        select(Search)
        .where(Search.user_id == user.id)
        .order_by(Search.created_at.desc())
        .limit(limit)
    )
    return list((await session.scalars(stmt)).all())


async def delete_search(session: AsyncSession, search: Search) -> None:
    await session.delete(search)
    await session.commit()
