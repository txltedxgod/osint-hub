"""Engine runners for Sherlock and Maigret.

Both tools are invoked as external CLIs via ``asyncio`` subprocesses (no shell,
so user input cannot be used for command injection). Found accounts are parsed
from the ``[+] Site: URL`` lines both engines print, which keeps the parser
independent of any particular tool version. If an engine binary is not
installed the runner degrades gracefully instead of crashing.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
from asyncio.subprocess import PIPE
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger("osint_hub.engines")

# Matches lines like: "[+] GitHub: https://github.com/user"
_FOUND_RE = re.compile(r"\[\+\]\s*(?P<site>[^:]+):\s*(?P<url>https?://\S+)")


@dataclass(slots=True)
class AccountHit:
    tool: str
    site_name: str
    url: str


@dataclass(slots=True)
class ToolRun:
    tool: str
    available: bool
    returncode: int | None = None
    hits: list[AccountHit] = field(default_factory=list)
    raw_output: str = ""
    error: str | None = None


def engine_available(binary: str) -> bool:
    return shutil.which(binary) is not None


def available_engines() -> dict[str, bool]:
    return {
        "sherlock": engine_available("sherlock"),
        "maigret": engine_available("maigret"),
    }


async def _run(cmd: list[str], timeout: int) -> tuple[int | None, str, str]:
    logger.info("Running: %s", " ".join(cmd))
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=PIPE, stderr=PIPE
        )
    except FileNotFoundError as exc:
        return None, "", str(exc)
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return None, "", f"timed out after {timeout}s"
    return (
        proc.returncode,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


def _parse_found(tool: str, text: str) -> list[AccountHit]:
    hits: list[AccountHit] = []
    seen: set[str] = set()
    for match in _FOUND_RE.finditer(text):
        site = match.group("site").strip()
        url = match.group("url").strip()
        key = f"{site}|{url}"
        if key in seen:
            continue
        seen.add(key)
        hits.append(AccountHit(tool=tool, site_name=site, url=url))
    return hits


async def run_sherlock(username: str) -> ToolRun:
    if not engine_available("sherlock"):
        return ToolRun("sherlock", available=False, error="sherlock is not installed")
    cmd = [
        "sherlock",
        username,
        "--print-found",
        "--no-color",
        "--timeout",
        str(settings.site_timeout),
    ]
    rc, out, err = await _run(cmd, settings.sherlock_timeout)
    return ToolRun(
        tool="sherlock",
        available=True,
        returncode=rc,
        hits=_parse_found("sherlock", out),
        raw_output=out,
        error=err.strip() or (None if rc is not None else "timed out"),
    )


async def run_maigret(username: str) -> ToolRun:
    if not engine_available("maigret"):
        return ToolRun("maigret", available=False, error="maigret is not installed")
    cmd = [
        "maigret",
        username,
        "--no-progressbar",
        "--timeout",
        str(settings.site_timeout),
    ]
    rc, out, err = await _run(cmd, settings.maigret_timeout)
    return ToolRun(
        tool="maigret",
        available=True,
        returncode=rc,
        hits=_parse_found("maigret", out),
        raw_output=out,
        error=err.strip() or (None if rc is not None else "timed out"),
    )


_RUNNERS = {"sherlock": run_sherlock, "maigret": run_maigret}


async def run_engines(username: str, tools: list[str]) -> list[ToolRun]:
    """Run the requested engines concurrently."""
    coros = [_RUNNERS[t](username) for t in tools if t in _RUNNERS]
    if not coros:
        return []
    return list(await asyncio.gather(*coros))
