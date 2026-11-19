-- Run once in Supabase SQL Editor. Keep service_role key SECRET.
create table if not exists public.trader_state (
  id integer primary key check (id = 1),
  state jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.trader_state enable row level security;
-- No public policies. Only service_role bypasses RLS.
