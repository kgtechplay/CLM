"""Server-side persistence for API responses in Supabase."""
from __future__ import annotations

from typing import Any

import httpx

from .settings import settings


class SupabaseStoreError(RuntimeError):
    pass


def _is_legacy_jwt_key(key: str) -> bool:
    return key.count(".") == 2


class SupabaseStore:
    def __init__(self) -> None:
        if not settings.supabase_url or not settings.supabase_secret_key:
            raise SupabaseStoreError("Supabase server credentials are not configured")
        self.endpoint = f"{settings.supabase_url.rstrip('/')}/rest/v1/api_responses"
        self.headers = self._headers()

    def _headers(self) -> dict[str, str]:
        key = settings.supabase_secret_key
        headers = {
            "apikey": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # New sb_secret_ keys are not JWTs. Sending them as Bearer tokens makes
        # PostgREST return Invalid JWT. Legacy service_role JWTs still need it.
        if _is_legacy_jwt_key(key):
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def get_response(self, idempotency_key: str) -> dict[str, Any] | None:
        response = self._request(
            "GET",
            f"?select=response&idempotency_key=eq.{idempotency_key}&limit=1",
        )
        rows = response.json()
        return rows[0]["response"] if rows else None

    def save_response(self, idempotency_key: str, conversation_id: str, response_body: dict[str, Any]) -> dict[str, Any]:
        headers = {**self.headers, "Prefer": "return=representation,resolution=ignore-duplicates"}
        response = self._request(
            "POST",
            "",
            headers=headers,
            json={
                "idempotency_key": idempotency_key,
                "conversation_id": conversation_id,
                "response": response_body,
            },
        )
        rows = response.json()
        if rows:
            return rows[0]["response"]
        stored = self.get_response(idempotency_key)
        if stored is None:
            raise SupabaseStoreError("Supabase did not return the stored response")
        return stored

    def _request(self, method: str, suffix: str, *, headers: dict[str, str] | None = None, json: dict[str, Any] | None = None) -> httpx.Response:
        try:
            response = httpx.request(method, f"{self.endpoint}{suffix}", headers=headers or self.headers, json=json, timeout=10)
        except httpx.HTTPError as exc:
            raise SupabaseStoreError("Supabase is unreachable") from exc
        if response.is_error:
            raise SupabaseStoreError(_describe_failure(response))
        return response


def _describe_failure(response: httpx.Response) -> str:
    body = (response.text or "").strip().replace("\n", " ")[:240]
    if response.status_code in {401, 403}:
        return f"Supabase rejected the API key with status {response.status_code}: {body}"
    if response.status_code == 404 or "PGRST205" in body or "could not find the table" in body.lower():
        return f"Supabase table public.api_responses is missing. Apply supabase/migrations/0002_api_response_store.sql. Status {response.status_code}: {body}"
    return f"Supabase request failed with status {response.status_code}: {body}"


store = SupabaseStore()
