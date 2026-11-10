"""Unit tests for password hashing, OSINT parsing, validation, and PDF generation."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models import Result, Search
from app.security import hash_password, verify_password
from app.services.osint import _parse_found
from app.services.pdf_service import build_search_pdf
from app.services.search_service import SearchError, validate_tools, validate_username


def test_password_hashing_and_verification() -> None:
    hashed, salt = hash_password("s3cret-pass!")
    assert verify_password("s3cret-pass!", hashed, salt)
    assert not verify_password("wrong-pass!", hashed, salt)

    hashed_two, salt_two = hash_password("s3cret-pass!")
    assert salt_two != salt
    assert hashed_two != hashed


def test_parse_found_deduplicates_hits() -> None:
    raw = (
        "[*] Checking username alice on 300 websites\n"
        "[+] GitHub: https://github.com/alice\n"
        "[+] GitLab: https://gitlab.com/alice\n"
        "[+] GitHub: https://github.com/alice\n"
    )
    hits = _parse_found("sherlock", raw)
    assert [(h.tool, h.site_name, h.url) for h in hits] == [
        ("sherlock", "GitHub", "https://github.com/alice"),
        ("sherlock", "GitLab", "https://gitlab.com/alice"),
    ]


def test_validate_username_and_tools() -> None:
    assert validate_username("  alice_01-dev.io  ") == "alice_01-dev.io"
    with pytest.raises(SearchError):
        validate_username("alice; rm -rf /")
    with pytest.raises(SearchError):
        validate_username("a")

    assert validate_tools(["maigret", "unknown", "sherlock"]) == ["sherlock", "maigret"]
    with pytest.raises(SearchError):
        validate_tools(["invalid-tool"])


def test_build_search_pdf_with_and_without_results() -> None:
    empty_search = Search(
        id=1,
        user_id=1,
        query="alice_01",
        tools="sherlock",
        status="completed",
        total_found=0,
        sites_checked=0,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        results=[],
    )
    empty_pdf = build_search_pdf(empty_search)
    assert empty_pdf.startswith(b"%PDF-")

    populated_search = Search(
        id=2,
        user_id=1,
        query="alice_01",
        tools="sherlock,maigret",
        status="completed",
        total_found=1,
        sites_checked=1,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        results=[
            Result(
                tool="sherlock",
                site_name="GitHub",
                url="https://github.com/alice_01",
            )
        ],
    )
    full_pdf = build_search_pdf(populated_search)
    assert full_pdf.startswith(b"%PDF-")
    assert len(full_pdf) > len(empty_pdf)
