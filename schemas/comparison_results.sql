create table if not exists public.comparison_results (
  email_id    text primary key,
  fields      jsonb not null default '[]'::jsonb,
  status      text not null default 'CLASSIFIED',
  result_text text,
  reason      text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

alter table public.comparison_results enable row level security;

create policy "authenticated read comparisons"
  on public.comparison_results for select to authenticated using (true);

create policy "authenticated write comparisons"
  on public.comparison_results for all to authenticated using (true);
