"""Authentication and password helpers for the server-only admin area."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Header, HTTPException

from .settings import settings


def issue_admin_token() -> str:
    _require_configured_password()
    payload = json.dumps({"exp": int(time.time()) + settings.admin_token_ttl_seconds}, separators=(",", ":")).encode()
    encoded = _encode(payload)
    signature = hmac.new(settings.admin_password.encode(), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{_encode(signature)}"


def require_admin(authorization: str = Header(...)) -> None:
    _require_configured_password()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or not _valid_token(token):
        raise HTTPException(status_code=401, detail="Admin authentication is required")


def password_matches(password: str) -> bool:
    _require_configured_password()
    return hmac.compare_digest(password, settings.admin_password)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${_encode(salt)}${_encode(digest)}"


def _valid_token(token: str) -> bool:
    encoded, separator, signature = token.partition(".")
    if not separator or not encoded or not signature:
        return False
    expected = _encode(hmac.new(settings.admin_password.encode(), encoded.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        payload = json.loads(_decode(encoded))
        return int(payload["exp"]) > time.time()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _require_configured_password() -> None:
    if not settings.admin_password:
        raise HTTPException(status_code=503, detail="Admin_Password is not configured")


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(f"{value}{'=' * (-len(value) % 4)}")
