"""Password hashing helpers (PBKDF2-HMAC-SHA256, stdlib only)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

_PBKDF2_ROUNDS = 200_000
_ALGO = "sha256"


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Return (hex_hash, hex_salt). Generates a random salt if none supplied."""
    if salt is None:
        salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        _ALGO, password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ROUNDS
    )
    return derived.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)
