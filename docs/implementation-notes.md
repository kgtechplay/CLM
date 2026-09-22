# Implementation notes

## Specification decisions implemented

- The chat interface never displays a partial reply. It waits for the API response and presents a child-friendly fallback when the service is unavailable.
- The API accepts an idempotency key, limits message size, applies a basic per-IP rate limit, chooses the most restrictive input outcome, and avoids putting secrets or prompt text in client responses.
- Help-seeking language routes to a supportive trusted-adult message instead of an empty refusal. Harmful procedural requests do not reach generation.
- The API has no browser-side provider key. It deliberately operates in safe local-demo mode until the required production safety controls are complete.
- The schema establishes child-owned conversations/messages and enables RLS on every exposed table. Browser writes are intentionally absent; production writes belong behind server authorization.
- Safety profile versions are immutable rows with age/reading guidance and distinct input/output thresholds. A child references one active version.

## Required before production

This MVP is not approved for real child data. The supplied requirements leave decisions that must be made before that point: child age/jurisdiction, consent and OpenAI under-18 privacy controls, retention periods, guardian visibility, and high-risk escalation process. Complete authenticated Supabase repositories, server-side role checks, RLS tests, calibrated provider moderation, output moderation/rewrite, review/audit flows, and a safety evaluation suite before enabling model generation.
