-- Apply through the Supabase migration workflow. RLS policies must be tested
-- with child, guardian, administrator, and anonymous roles before production.
create extension if not exists "pgcrypto";
create extension if not exists vector;

create type public.app_role as enum ('child', 'guardian', 'admin');
create type public.message_role as enum ('user', 'assistant');
create type public.approval_state as enum ('candidate', 'approved', 'rejected', 'revised', 'archived');

create table public.profiles (id uuid primary key references auth.users(id) on delete cascade, display_name text not null check (char_length(display_name) between 1 and 80), status text not null default 'active', created_at timestamptz not null default now());
create table public.user_roles (user_id uuid primary key references public.profiles(id) on delete cascade, role public.app_role not null, granted_by uuid references public.profiles(id), granted_at timestamptz not null default now());
create table public.safety_profile_definitions (id uuid primary key default gen_random_uuid(), name text unique not null, description text, created_at timestamptz not null default now());
create table public.safety_profile_versions (id uuid primary key default gen_random_uuid(), safety_profile_id uuid not null references public.safety_profile_definitions(id) on delete cascade, version integer not null, status text not null check (status in ('draft', 'active', 'retired')), age_band text not null, reading_level text not null, language text not null default 'en', prompt_content text not null, input_thresholds jsonb not null, output_thresholds jsonb not null, created_by uuid references public.profiles(id), created_at timestamptz not null default now(), unique (safety_profile_id, version));
create table public.child_profiles (id uuid primary key default gen_random_uuid(), auth_user_id uuid unique not null references public.profiles(id) on delete cascade, guardian_user_id uuid references public.profiles(id), age_band text not null, grade_level text, locale text not null default 'en', active_safety_profile_version uuid not null references public.safety_profile_versions(id), created_at timestamptz not null default now());
create table public.conversations (id uuid primary key default gen_random_uuid(), child_profile_id uuid not null references public.child_profiles(id) on delete cascade, title text not null default 'New conversation', summary text, status text not null default 'active', last_message_at timestamptz not null default now());
create table public.messages (id uuid primary key default gen_random_uuid(), conversation_id uuid not null references public.conversations(id) on delete cascade, role public.message_role not null, content text not null, safety_state text not null, created_at timestamptz not null default now());
create table public.topics (id uuid primary key default gen_random_uuid(), parent_id uuid references public.topics(id), name text not null, slug text unique not null, active boolean not null default true, taxonomy_version integer not null default 1);
create table public.knowledge_items (id uuid primary key default gen_random_uuid(), question text not null, answer text not null, approval_state public.approval_state not null default 'candidate', audience text not null, source_message_id uuid references public.messages(id), approved_by uuid references public.profiles(id), created_at timestamptz not null default now());
create table public.safety_events (id uuid primary key default gen_random_uuid(), child_profile_id uuid not null references public.child_profiles(id) on delete cascade, message_id uuid references public.messages(id) on delete set null, category text not null, severity text not null, action text not null, profile_version_id uuid, created_at timestamptz not null default now());
create index conversations_owner_recent_idx on public.conversations (child_profile_id, last_message_at desc);
create index messages_conversation_created_idx on public.messages (conversation_id, created_at);

alter table public.profiles enable row level security;
alter table public.user_roles enable row level security;
alter table public.safety_profile_definitions enable row level security;
alter table public.safety_profile_versions enable row level security;
alter table public.child_profiles enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.topics enable row level security;
alter table public.knowledge_items enable row level security;
alter table public.safety_events enable row level security;

-- Child users can read only their own profile data. Message policy uses the
-- conversation ownership chain, so guessed IDs never cross child boundaries.
create policy "child reads own child profile" on public.child_profiles for select using (auth.uid() = auth_user_id);
create policy "child reads own conversations" on public.conversations for select using (child_profile_id in (select id from public.child_profiles where auth_user_id = auth.uid()));
create policy "child reads own messages" on public.messages for select using (conversation_id in (select c.id from public.conversations c join public.child_profiles cp on cp.id = c.child_profile_id where cp.auth_user_id = auth.uid()));
-- Writes and all administrative access are intentionally performed via the
-- server using trusted role checks; no browser write policy is created here.
