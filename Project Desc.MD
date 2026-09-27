# BrightPath Learning Assistant

BrightPath is a small learning-chat MVP designed for children. It has a React browser interface, a FastAPI backend that enforces safety rules, optional OpenAI-powered answers, and Supabase persistence for API response idempotency.

## Architecture

```text
React + Vite browser UI
        |
        | POST /v1/chat/messages
        v
FastAPI safety boundary
        |-- checks rate limits and harmful/sensitive content
        |-- chooses a safe local reply or optional OpenAI reply
        |-- stores and retrieves idempotent responses
        v
Supabase REST API
        |
        v
Postgres database
```

The browser never receives the Supabase secret key or OpenAI API key. Those values are used only by the FastAPI server.

## Repository layout

| Path | Purpose |
| --- | --- |
| `apps/web` | React + Vite child-facing chat interface. |
| `apps/api` | FastAPI backend, safety logic, optional LLM client, and Supabase store. |
| `supabase/migrations` | Database schema migrations. |
| `package.json` | Root shortcuts for starting the web app, API, and web build. |

## Browser application

`apps/web/src/main.tsx` renders the chat screen, starter conversations, guardian/demo settings, and the optional AI-answer toggle.

When a child submits a question, the UI:

1. Creates a browser-side message ID with `crypto.randomUUID()`.
2. Adds the child's message to the current local conversation immediately.
3. Sends the question to `POST /v1/chat/messages` with that ID in the `Idempotency-Key` header.
4. Adds the returned safe answer to the UI.

The current UI keeps its conversation list and message history in React state. Its built-in starter conversations are demo data; it does not yet load the relational `conversations` and `messages` tables from Supabase.

## API request flow

The backend entry point is `apps/api/app/main.py`.

### Health check

`GET /health` reports whether the optional LLM is configured and whether the Supabase response store is reachable. In non-production environments it also returns a concise database error description.

### Chat endpoint

`POST /v1/chat/messages` accepts:

```json
{
  "conversation_id": "browser conversation identifier",
  "content": "child question",
  "use_llm": false
}
```

The request must include `Idempotency-Key`. The backend first looks up that key in Supabase. If an earlier response exists, it returns the stored response instead of generating another answer.

For a new request, the backend:

1. Applies a simple IP-based rate limit of 20 requests per minute.
2. Classifies the question as `allow`, `guided`, `block`, or `support`.
3. Immediately returns safe support guidance for self-harm/abuse language and safe refusal guidance for harmful procedures. These messages never reach the LLM.
4. Uses a local educational template by default.
5. Calls OpenAI only when the LLM is configured and the request allows it. Input and output moderation can be enabled with environment settings.
6. Stores the final API response in Supabase and returns it to the browser.

## Supabase persistence

`apps/api/app/supabase_store.py` calls the Supabase REST API with the server-only `SUPABASE_SECRET_KEY`.

The API has four active default safety profiles: `Less than 10`, `10-13`, `13-15`, and `15-17`. Each profile version stores a prompt plus input and output caps for all OpenAI moderation score categories. LLM requests default to `Less than 10`; API callers can set the `safety_profile` request field to another supported profile. The backend loads that profile from Supabase, applies its input and output thresholds, and appends its prompt to the LLM system instructions.

Active profiles are cached in the API process for `SAFETY_PROFILE_CACHE_TTL_SECONDS` (five minutes by default). Saving a profile from the admin area immediately invalidates its cached entry.

The application currently persists idempotency records in `public.api_responses`:

| Column | Purpose |
| --- | --- |
| `id` | Database-generated UUID. |
| `idempotency_key` | Unique request key from the browser. |
| `conversation_id` | Browser conversation identifier associated with the reply. |
| `response` | JSON copy of the API response. |
| `created_at` | Record timestamp. |

This prevents duplicate answers if the browser retries the same request. Row Level Security is enabled; access is intentionally performed by the backend with a secret key.

`0001_foundation.sql` also creates the longer-term domain schema: profiles, roles, safety profiles, child profiles, conversations, messages, topics, knowledge items, and safety events. Those tables are prepared for authenticated, child-owned data, but the browser authentication and repository layer for them are not implemented yet.

## Configuration

Copy the example environment files and fill in only your own values:

```text
apps/api/.env.example  -> apps/api/.env
apps/web/.env.example  -> apps/web/.env
```

Important API variables:

| Variable | Use |
| --- | --- |
| `SUPABASE_URL` | Base project URL, such as `https://your-project.supabase.co`. Do not append `/rest/v1`. |
| `SUPABASE_SECRET_KEY` | Server-only `sb_secret_...` key used by FastAPI for Supabase writes and reads. |
| `SUPABASE_PUBLISHABLE_KEY` | Available for future non-privileged server/client use; not used by the current FastAPI store. |
| `DATABASE_URL` / `DATABASE_DIRECT_URL` | Reserved for future direct Postgres access; the current API uses Supabase REST instead. |
| `OPENAI_API_KEY` | Optional server-only key to enable model-generated learning replies. |
| `LLM_ENABLED` | Enables LLM responses by default when an OpenAI key is available. |
| `LLM_MODERATION_ENABLED` | Enables OpenAI moderation before and after optional generation. |
| `Admin_Password` | Server-only password for the `admin` login. Required before the admin page can be used. |

Important web variables:

| Variable | Use |
| --- | --- |
| `VITE_API_BASE_URL` | FastAPI base URL, normally `http://localhost:8000`. |
| `VITE_SUPABASE_URL` / `VITE_SUPABASE_PUBLISHABLE_KEY` | Reserved for future browser Supabase authentication; do not place a secret key here. |

Keep every secret key out of source control and browser-exposed `VITE_` variables.

## Database migrations

The deployed Supabase project should include:

1. `0001_foundation.sql` — primary application tables, types, indexes, RLS, and child read policies.
2. `0002_api_response_store.sql` — idempotent API response storage.
3. `0003_default_safety_profiles.sql` — four default age-band profiles, prompts, and moderation score caps.
4. `0004_admin_users.sql` — admin-managed users with internal UUIDs, salted password hashes, and safety-profile links.

## Administration

Select **Admin settings** in the browser UI and sign in as `admin` with the value in `Admin_Password`. The browser receives a short-lived session token and can use two protected tabs:

- **User management** creates and edits a user's name, optional email, username, password, and selected safety profile. The internal UUID is retained by the API but never rendered in the UI.
- **Safety profiles** edits the prompt and all input/output moderation score caps for each age band. The FastAPI server reads the active profile before every LLM call.

User passwords are salted and hashed with `scrypt` before storage. The admin password and Supabase secret key are never sent to the browser.

Apply migrations through the Supabase CLI or the authenticated Supabase management connection. After schema changes, verify table existence and review Supabase security advisors.

## Run locally

Install JavaScript dependencies inside `apps/web`, then start the two processes in separate terminals:

```powershell
npm --prefix apps/web install
npm run dev
```

```powershell
python -m pip install -r apps/api/requirements.txt
npm run api
```

The web app is normally served by Vite on `http://localhost:5173`; the API runs on `http://localhost:8000`.

Build the web app with:

```powershell
npm run build
```

## Current limitations and next steps

- The UI is a demo client with local conversation state; it does not yet authenticate users or read/write the relational chat tables.
- The API rate limiter is in memory and resets when the API process restarts.
- The database schema has RLS enabled, but several future/admin tables still require deliberate policies before browser access is added.
- A production implementation should add Supabase Auth, create child/guardian profiles, persist conversations and messages through server repositories, and replace the simple per-process rate limit with a shared store.
