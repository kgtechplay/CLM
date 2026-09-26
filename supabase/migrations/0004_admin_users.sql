create table public.app_users (
  id uuid primary key default gen_random_uuid(),
  display_name text not null check (char_length(display_name) between 1 and 120),
  email text unique,
  username text unique not null check (char_length(username) between 3 and 80),
  password_hash text not null,
  safety_profile_version_id uuid references public.safety_profile_versions(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

update public.app_users
set safety_profile_version_id = (
  select versions.id
  from public.safety_profile_versions versions
  join public.safety_profile_definitions definitions on definitions.id = versions.safety_profile_id
  where definitions.name = 'Less than 10' and versions.status = 'active'
  order by versions.version desc
  limit 1
)
where safety_profile_version_id is null;

alter table public.app_users alter column safety_profile_version_id set not null;
alter table public.app_users enable row level security;
