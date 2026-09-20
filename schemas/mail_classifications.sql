create table if not exists public.mail_classifications (
  email_id text primary key,
  category text not null,
  confidence numeric not null default 0,
  scores jsonb not null default '{}'::jsonb,
  check_required boolean not null default false,
  review_reason text,
  status text not null default 'CLASSIFIED',
  corrected_values jsonb,
  corrected_by uuid references auth.users(id),
  updated_at timestamptz not null default now()
);
alter table public.mail_classifications enable row level security;
create policy "authenticated users can read classifications" on public.mail_classifications for select to authenticated using (true);
create policy "authenticated users can update classifications" on public.mail_classifications for update to authenticated using (true);
