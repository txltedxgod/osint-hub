"""Registration, login and logout routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models import User
from app.security import hash_password, verify_password
from app.templating import templates

logger = logging.getLogger("osint_hub.auth")
router = APIRouter(tags=["auth"])


@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse(
        "register.html", {"request": request, "user": None}
    )


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    username = username.strip()
    error = None
    if len(username) < 3 or len(username) > 64:
        error = "Username must be 3-64 characters long."
    elif len(password) < 6:
        error = "Password must be at least 6 characters long."
    elif password != password2:
        error = "Passwords do not match."
    else:
        exists = await session.scalar(
            select(User).where(func.lower(User.username) == username.lower())
        )
        if exists:
            error = "This username is already taken."

    if error:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "user": None, "error": error, "username": username},
            status_code=400,
        )

    # The very first registered account becomes an administrator.
    is_first = (await session.scalar(select(func.count(User.id)))) == 0
    pwd_hash, salt = hash_password(password)
    user = User(
        username=username,
        password_hash=pwd_hash,
        salt=salt,
        is_admin=is_first,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    request.session["user_id"] = user.id
    logger.info("New user registered: %s (admin=%s)", user.username, user.is_admin)
    return RedirectResponse("/", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse(
        "login.html", {"request": request, "user": None}
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    username = username.strip()
    user = await session.scalar(
        select(User).where(func.lower(User.username) == username.lower())
    )
    if not user or not verify_password(password, user.password_hash, user.salt):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "user": None,
                "error": "Invalid username or password.",
                "username": username,
            },
            status_code=401,
        )
    request.session["user_id"] = user.id
    logger.info("User logged in: %s", user.username)
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
