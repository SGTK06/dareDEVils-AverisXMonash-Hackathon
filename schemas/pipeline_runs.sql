create table if not exists public.pipeline_runs (
  id          uuid primary key default gen_random_uuid(),
  run_type    text not null check (run_type in ('classification_test', 'full_pipeline', 'submission')),
  status      text not null default 'running' check (status in ('running', 'success', 'failed')),
  config      jsonb not null default '{}'::jsonb,
  results     jsonb,
  score       numeric,
  email_count integer,
  started_at  timestamptz not null default now(),
  finished_at timestamptz,
  started_by  uuid references auth.users(id)
);

create index idx_pipeline_runs_type_date
  on public.pipeline_runs (run_type, started_at desc);

alter table public.pipeline_runs enable row level security;

create policy "authenticated read runs"
  on public.pipeline_runs for select to authenticated using (true);

create policy "authenticated write runs"
  on public.pipeline_runs for insert to authenticated with check (true);

create policy "authenticated update runs"
  on public.pipeline_runs for update to authenticated using (true);
