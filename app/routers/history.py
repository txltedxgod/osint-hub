"""Search-history listing, detail, PDF export and deletion."""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.services import search_service
from app.services.pdf_service import build_search_pdf
from app.templating import templates

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_class=HTMLResponse)
async def history(
    request: Request, session: AsyncSession = Depends(get_session)
):
    user = await get_current_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)
    searches = await search_service.list_searches(session, user, limit=200)
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"user": user, "searches": searches},
    )


@router.get("/{search_id}", response_class=HTMLResponse)
async def history_detail(
    search_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = await get_current_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)
    search = await search_service.get_search(session, search_id, user)
    if not search:
        return RedirectResponse("/history", status_code=303)

    grouped: dict[str, list] = defaultdict(list)
    for res in search.results:
        grouped[res.tool].append(res)
    return templates.TemplateResponse(
        request=request,
        name="history_detail.html",
        context={
            "user": user,
            "search": search,
            "grouped": dict(grouped),
        },
    )


@router.get("/{search_id}/pdf")
async def history_pdf(
    search_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = await get_current_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)
    search = await search_service.get_search(session, search_id, user)
    if not search:
        return RedirectResponse("/history", status_code=303)

    pdf_bytes = build_search_pdf(search)
    filename = f"osint_{search.query}_{search.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{search_id}/delete")
async def history_delete(
    search_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = await get_current_user(request, session)
    if not user:
        return RedirectResponse("/login", status_code=303)
    search = await search_service.get_search(session, search_id, user)
    if search:
        await search_service.delete_search(session, search)
    return RedirectResponse("/history", status_code=303)
