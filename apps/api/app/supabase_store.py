"""Server-side persistence for API responses and safety profiles in Supabase."""
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
import time
from typing import Any
from urllib.parse import quote

import httpx

from .settings import settings


class SupabaseStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class SafetyProfile:
    name: str
    age_band: str
    reading_level: str
    prompt_content: str
    input_thresholds: dict[str, float]
    output_thresholds: dict[str, float]


def _is_legacy_jwt_key(key: str) -> bool:
    return key.count(".") == 2


class SupabaseStore:
    def __init__(self) -> None:
        if not settings.supabase_url or not settings.supabase_secret_key:
            raise SupabaseStoreError("Supabase server credentials are not configured")
        self.rest_url = f"{settings.supabase_url.rstrip('/')}/rest/v1"
        self.endpoint = f"{self.rest_url}/api_responses"
        self.headers = self._headers()
        self._profile_cache: dict[str, tuple[float, SafetyProfile]] = {}
        self._profile_cache_lock = Lock()

    def _headers(self) -> dict[str, str]:
        key = settings.supabase_secret_key
        headers = {
            "apikey": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if _is_legacy_jwt_key(key):
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def get_response(self, idempotency_key: str) -> dict[str, Any] | None:
        response = self._request(
            "GET",
            f"{self.endpoint}?select=response&idempotency_key=eq.{idempotency_key}&limit=1",
        )
        rows = response.json()
        return rows[0]["response"] if rows else None

    def save_response(self, idempotency_key: str, conversation_id: str, response_body: dict[str, Any]) -> dict[str, Any]:
        headers = {**self.headers, "Prefer": "return=representation,resolution=ignore-duplicates"}
        response = self._request(
            "POST",
            self.endpoint,
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

    def get_active_safety_profile(self, name: str) -> SafetyProfile:
        with self._profile_cache_lock:
            cached = self._profile_cache.get(name)
            if cached and cached[0] > time.monotonic():
                return cached[1]
        profile = self._fetch_active_safety_profile(name)
        ttl = max(settings.safety_profile_cache_ttl_seconds, 0)
        if ttl:
            with self._profile_cache_lock:
                self._profile_cache[name] = (time.monotonic() + ttl, profile)
        return profile

    def _fetch_active_safety_profile(self, name: str) -> SafetyProfile:
        profile_name = quote(name, safe="")
        definitions = self._request(
            "GET",
            f"{self.rest_url}/safety_profile_definitions?select=id,name&name=eq.{profile_name}&limit=1",
        ).json()
        if not definitions:
            raise SupabaseStoreError(f"Safety profile {name!r} was not found")
        definition = definitions[0]
        versions = self._request(
            "GET",
            f"{self.rest_url}/safety_profile_versions?select=age_band,reading_level,prompt_content,input_thresholds,output_thresholds&"
            f"safety_profile_id=eq.{definition['id']}&status=eq.active&order=version.desc&limit=1",
        ).json()
        if not versions:
            raise SupabaseStoreError(f"Safety profile {name!r} has no active version")
        version = versions[0]
        return SafetyProfile(
            name=definition["name"],
            age_band=version["age_band"],
            reading_level=version["reading_level"],
            prompt_content=version["prompt_content"],
            input_thresholds=_thresholds(version["input_thresholds"]),
            output_thresholds=_thresholds(version["output_thresholds"]),
        )

    def list_safety_profiles(self) -> list[dict[str, Any]]:
        definitions = self._request("GET", f"{self.rest_url}/safety_profile_definitions?select=id,name,description&order=name").json()
        versions = self._request("GET", f"{self.rest_url}/safety_profile_versions?select=id,safety_profile_id,version,age_band,reading_level,prompt_content,input_thresholds,output_thresholds&status=eq.active&order=version.desc").json()
        latest: dict[str, dict[str, Any]] = {}
        for version in versions:
            latest.setdefault(version["safety_profile_id"], version)
        return [
            {
                "name": definition["name"],
                "description": definition["description"],
                **latest[definition["id"]],
            }
            for definition in definitions
            if definition["id"] in latest
        ]

    def update_safety_profile(self, name: str, prompt_content: str, input_thresholds: dict[str, float], output_thresholds: dict[str, float]) -> dict[str, Any]:
        profile = self._fetch_active_safety_profile(name)
        rows = self._request(
            "PATCH",
            f"{self.rest_url}/safety_profile_versions?safety_profile_id=eq.{self._definition_id(name)}&status=eq.active",
            headers={**self.headers, "Prefer": "return=representation"},
            json={"prompt_content": prompt_content, "input_thresholds": input_thresholds, "output_thresholds": output_thresholds},
        ).json()
        if not rows:
            raise SupabaseStoreError(f"Safety profile {profile.name!r} has no active version")
        with self._profile_cache_lock:
            self._profile_cache.pop(name, None)
        return rows[0]

    def list_users(self) -> list[dict[str, Any]]:
        users = self._request("GET", f"{self.rest_url}/app_users?select=id,display_name,email,username,safety_profile_version_id&order=display_name").json()
        profiles = self.list_safety_profiles()
        names = {profile["id"]: profile["name"] for profile in profiles}
        return [{**user, "safety_profile": names.get(user["safety_profile_version_id"], "Less than 10")} for user in users]

    def create_user(self, name: str, email: str | None, username: str, password_hash: str, safety_profile: str) -> dict[str, Any]:
        version_id = self._profile_version_id(safety_profile)
        rows = self._request(
            "POST",
            f"{self.rest_url}/app_users",
            headers={**self.headers, "Prefer": "return=representation"},
            json={"display_name": name, "email": email, "username": username, "password_hash": password_hash, "safety_profile_version_id": version_id},
        ).json()
        return rows[0]

    def update_user(self, user_id: str, values: dict[str, Any], safety_profile: str | None = None) -> dict[str, Any]:
        if safety_profile is not None:
            values["safety_profile_version_id"] = self._profile_version_id(safety_profile)
        rows = self._request(
            "PATCH",
            f"{self.rest_url}/app_users?id=eq.{quote(user_id, safe='')}",
            headers={**self.headers, "Prefer": "return=representation"},
            json=values,
        ).json()
        if not rows:
            raise SupabaseStoreError("User was not found")
        return rows[0]

    def _definition_id(self, name: str) -> str:
        definitions = self._request("GET", f"{self.rest_url}/safety_profile_definitions?select=id&name=eq.{quote(name, safe='')}&limit=1").json()
        if not definitions:
            raise SupabaseStoreError(f"Safety profile {name!r} was not found")
        return definitions[0]["id"]

    def _profile_version_id(self, name: str) -> str:
        definition_id = self._definition_id(name)
        versions = self._request("GET", f"{self.rest_url}/safety_profile_versions?select=id&safety_profile_id=eq.{definition_id}&status=eq.active&order=version.desc&limit=1").json()
        if not versions:
            raise SupabaseStoreError(f"Safety profile {name!r} has no active version")
        return versions[0]["id"]

    def _request(self, method: str, url: str, *, headers: dict[str, str] | None = None, json: dict[str, Any] | None = None) -> httpx.Response:
        try:
            response = httpx.request(method, url, headers=headers or self.headers, json=json, timeout=10)
        except httpx.HTTPError as exc:
            raise SupabaseStoreError("Supabase is unreachable") from exc
        if response.is_error:
            raise SupabaseStoreError(_describe_failure(response))
        return response


def _thresholds(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        raise SupabaseStoreError("Safety profile thresholds must be a JSON object")
    thresholds: dict[str, float] = {}
    for category, maximum in value.items():
        if not isinstance(category, str) or not isinstance(maximum, (int, float)) or not 0 <= maximum <= 1:
            raise SupabaseStoreError("Safety profile thresholds must contain scores between 0 and 1")
        thresholds[category] = float(maximum)
    return thresholds


def _describe_failure(response: httpx.Response) -> str:
    body = (response.text or "").strip().replace("\n", " ")[:240]
    if response.status_code in {401, 403}:
        return f"Supabase rejected the API key with status {response.status_code}: {body}"
    if response.status_code == 404 or "PGRST205" in body or "could not find the table" in body.lower():
        return f"Supabase table public.api_responses is missing. Apply the required migration. Status {response.status_code}: {body}"
    return f"Supabase request failed with status {response.status_code}: {body}"


store = SupabaseStore()
