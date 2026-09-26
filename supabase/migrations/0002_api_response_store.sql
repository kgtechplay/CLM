create table public.api_responses (id uuid primary key default gen_random_uuid(), idempotency_key text unique not null, conversation_id text not null, response jsonb not null, created_at timestamptz not null default now());
alter table public.api_responses enable row level security;
