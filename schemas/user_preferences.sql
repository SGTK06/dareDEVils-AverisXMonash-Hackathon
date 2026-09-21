create table if not exists public.user_preferences (
  user_id     uuid primary key references auth.users(id),
  theme       text not null default 'light' check (theme in ('light', 'dark', 'system')),
  last_view   text default 'inbox',
  filters     jsonb not null default '{}'::jsonb,
  updated_at  timestamptz not null default now()
);

alter table public.user_preferences enable row level security;

create policy "users read own preferences"
  on public.user_preferences for select to authenticated
  using (auth.uid() = user_id);

create policy "users write own preferences"
  on public.user_preferences for all to authenticated
  using (auth.uid() = user_id);
