-- ─────────────────────────────────────────────────────────────
-- Normclaim · Supabase Migration
-- File: 001_create_profiles.sql
-- Run in: Supabase Dashboard → SQL Editor
-- ─────────────────────────────────────────────────────────────

-- 1. PROFILES TABLE
-- Mirrors auth.users with claim-specific role metadata.
create table if not exists public.profiles (
  id              uuid primary key references auth.users(id) on delete cascade,
  email           text not null,
  name            text not null default '',
  role            text not null default 'HOSPITAL'
                    check (role in ('HOSPITAL', 'TPA', 'FINANCE')),
  hospital_id     text,
  tpa_officer_id  text,
  finance_user_id text,
  avatar_url      text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- 2. ROW LEVEL SECURITY
alter table public.profiles enable row level security;

-- Users can read their own profile
create policy "profiles: own read"
  on public.profiles for select
  using (auth.uid() = id);

-- Users can update their own profile
create policy "profiles: own update"
  on public.profiles for update
  using (auth.uid() = id);

-- Service role can do everything (for server-side operations)
create policy "profiles: service full access"
  on public.profiles
  using (auth.role() = 'service_role');

-- 3. AUTO-CREATE PROFILE ON SIGNUP
-- Triggered when a new user is created in auth.users
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, email, name, role)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'name', split_part(new.email, '@', 1)),
    coalesce(new.raw_user_meta_data->>'role', 'HOSPITAL')
  );
  return new;
end;
$$;

create or replace trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- 4. AUTO-UPDATE updated_at
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute procedure public.set_updated_at();

-- 5. INDEXES
create index if not exists profiles_role_idx on public.profiles(role);
create index if not exists profiles_hospital_id_idx on public.profiles(hospital_id);
create index if not exists profiles_tpa_officer_id_idx on public.profiles(tpa_officer_id);
