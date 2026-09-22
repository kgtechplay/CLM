# BrightPath child-safe learning assistant

This workspace contains a runnable MVP based on the supplied requirements:

- `apps/web` — React + TypeScript child chat interface and guardian safety-profile preview.
- `apps/api` — FastAPI safety boundary with idempotency, payload limits, rate limiting, safe routing and child-friendly fallbacks.
- `supabase/migrations` — initial ownership-focused schema and RLS foundation.

## Run locally

1. Install the web dependencies: `npm --prefix apps/web install`
2. Install the API dependencies: `python -m pip install -r apps/api/requirements.txt`
3. Start the API: `npm run api`
4. In another terminal, start the web app: `npm run dev`

No API key is needed to explore the MVP. The API intentionally serves safe deterministic learning replies until authentication, production moderation calibration, retention decisions, and under-18 privacy requirements are configured.

## Before connecting real child data

Do not enable OpenAI calls merely by adding an API key. Complete Supabase Auth and server-side role verification, calibrated input and output moderation, reviewed safety-profile versions, output rewrite/fallback handling, RLS tests, retention policies, and applicable privacy/consent review first.
