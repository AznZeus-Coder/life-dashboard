-- Daybook cloud-sync schema
create table if not exists public.daybook_data (
  user_id uuid primary key references auth.users(id) on delete cascade,
  data jsonb not null default '{"tasks":[],"chores":[]}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.daybook_data enable row level security;

create policy "Users can read their own Daybook data"
on public.daybook_data for select
using (auth.uid() = user_id);

create policy "Users can create their own Daybook data"
on public.daybook_data for insert
with check (auth.uid() = user_id);

create policy "Users can update their own Daybook data"
on public.daybook_data for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
