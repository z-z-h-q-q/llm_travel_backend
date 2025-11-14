-- infra/supabase/travel_plans.sql
-- Create travel_plans table with Row Level Security (RLS) and policies
-- Usage: run this in Supabase SQL Editor or via supabase CLI

-- 1) Ensure uuid generation extension
create extension if not exists "pgcrypto";

-- 2) Create table (idempotent)
create table if not exists public.travel_plans (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  title text,
  data jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 3) Index to speed queries by owner
create index if not exists idx_travel_plans_owner_id on public.travel_plans (owner_id);

-- 4) Enable RLS
alter table public.travel_plans enable row level security;

-- 5) Remove any conflicting policies if they exist (safe to run multiple times)
drop policy if exists "Allow owners to select their rows" on public.travel_plans;
drop policy if exists "Allow owners to insert their rows" on public.travel_plans;
drop policy if exists "Allow owners to update their rows" on public.travel_plans;
drop policy if exists "Allow owners to delete their rows" on public.travel_plans;

-- 6) Create policies
-- Select: allow users to read only their own rows
create policy "Allow owners to select their rows" on public.travel_plans
  for select
  using (owner_id = auth.uid());

-- Insert: require that inserted row's owner_id equals auth.uid()
-- Note: POST/INSERT policies cannot include USING; only WITH CHECK is applied
create policy "Allow owners to insert their rows" on public.travel_plans
  for insert
  with check (owner_id = auth.uid());

-- Update: allow updates only to rows the user owns, and ensure resulting owner_id still equals auth.uid()
create policy "Allow owners to update their rows" on public.travel_plans
  for update
  using (owner_id = auth.uid())
  with check (owner_id = auth.uid());

-- Delete: allow users to delete their own rows
create policy "Allow owners to delete their rows" on public.travel_plans
  for delete
  using (owner_id = auth.uid());

-- 7) Optional: trigger to keep updated_at column current
create or replace function public.set_updated_at()
  returns trigger
  language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_travel_plans_updated_at on public.travel_plans;
create trigger trg_travel_plans_updated_at
  before update on public.travel_plans
  for each row
  execute function public.set_updated_at();

-- End of travel_plans.sql
