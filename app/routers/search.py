"""Dashboard and username search routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.services import osint, search_service
from app.services.search_service import SearchError
from app.templating import templates

router = APIRouter(tags=["search"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request, session: AsyncSession = Depends(get_session)
):
    user = await get_current_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    searches = await search_service.list_searches(session, user, limit=10)
    total_accounts = sum(s.total_found for s in searches)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "searches": searches,
            "engines": osint.available_engines(),
            "total_accounts": total_accounts,
        },
    )


@router.post("/search")
async def run_search(
    request: Request,
    username: str = Form(...),
    tools: list[str] = Form(default=[]),
    session: AsyncSession = Depends(get_session),
):
    user = await get_current_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    try:
        search = await search_service.perform_search(
            session, user, username, tools
        )
    except SearchError as exc:
        searches = await search_service.list_searches(session, user, limit=10)
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "user": user,
                "searches": searches,
                "engines": osint.available_engines(),
                "total_accounts": sum(s.total_found for s in searches),
                "error": str(exc),
                "username": username,
            },
            status_code=400,
        )

    return RedirectResponse(f"/history/{search.id}", status_code=303)
