"""Integration tests covering auth, HTML views, search persistence, IDOR, and PDF export."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import database, main
from app.models import Base
from app.services import osint
from app.services.osint import AccountHit, ToolRun


@pytest.fixture()
def isolated_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    db_file = tmp_path / "test_osint.db"
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file.as_posix()}", echo=False, future=True
    )
    test_session_maker = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    monkeypatch.setattr(main.settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    monkeypatch.setattr(main.settings, "reports_dir", str(reports_dir))
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "async_session", test_session_maker)

    async def test_init_db() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(main, "init_db", test_init_db)

    async def fake_run_engines(username: str, tools: list[str]) -> list[ToolRun]:
        return [
            ToolRun(
                tool=tool,
                available=True,
                returncode=0,
                hits=[
                    AccountHit(
                        tool=tool,
                        site_name="GitHub",
                        url=f"https://github.com/{username}",
                    )
                ],
            )
            for tool in tools
        ]

    monkeypatch.setattr(osint, "run_engines", fake_run_engines)

    app = main.create_app()
    with TestClient(app) as client:
        yield client


def test_health_and_html_auth_views(isolated_client: TestClient) -> None:
    res = isolated_client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    assert isolated_client.get("/login").status_code == 200
    assert isolated_client.get("/register").status_code == 200

    dash = isolated_client.get("/", follow_redirects=False)
    assert dash.status_code == 303
    assert dash.headers["location"] == "/login"


def test_register_search_pdf_and_idor_isolation(isolated_client: TestClient) -> None:
    reg1 = isolated_client.post(
        "/register",
        data={"username": "alice_admin", "password": "password123", "password2": "password123"},
        follow_redirects=False,
    )
    assert reg1.status_code == 303
    assert isolated_client.get("/").status_code == 200

    search_resp = isolated_client.post(
        "/search",
        data={"username": "target_user", "tools": ["sherlock"]},
        follow_redirects=False,
    )
    assert search_resp.status_code == 303
    history_location = search_resp.headers["location"]
    assert history_location.startswith("/history/")
    assert isolated_client.get("/history").status_code == 200
    assert isolated_client.get(history_location).status_code == 200

    pdf_resp = isolated_client.get(f"{history_location}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF-")

    isolated_client.get("/logout", follow_redirects=False)
    reg2 = isolated_client.post(
        "/register",
        data={"username": "bob_viewer", "password": "password456", "password2": "password456"},
        follow_redirects=False,
    )
    assert reg2.status_code == 303

    foreign_pdf = isolated_client.get(f"{history_location}/pdf", follow_redirects=False)
    assert foreign_pdf.status_code == 303
    assert foreign_pdf.headers["location"] == "/history"
