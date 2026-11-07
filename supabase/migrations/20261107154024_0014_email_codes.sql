-- Hime's own email one-time codes (6 digits), sent by the email-auth edge
-- function. Only the service role can touch these tables.
create table if not exists public.auth_email_codes (
  id bigint generated always as identity primary key,
  email text not null,
  code_hash text not null,
  attempts int not null default 0,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_at timestamptz,
  ip text
);
create index if not exists auth_email_codes_email_idx on public.auth_email_codes (email, created_at desc);
alter table public.auth_email_codes enable row level security;
revoke all on public.auth_email_codes from public, anon, authenticated;

create table if not exists public.auth_rate_events (
  id bigint generated always as identity primary key,
  bucket text not null,
  created_at timestamptz not null default now()
);
create index if not exists auth_rate_events_bucket_idx on public.auth_rate_events (bucket, created_at desc);
alter table public.auth_rate_events enable row level security;
revoke all on public.auth_rate_events from public, anon, authenticated;

insert into public.app_secrets (key, value)
values ('otp_pepper', encode(extensions.gen_random_bytes(32), 'hex'))
on conflict (key) do nothing;

create or replace function public.auth_user_by_email(p_email text)
returns table (id uuid, confirmed boolean)
language sql stable security definer set search_path = ''
as $$
  select u.id, u.email_confirmed_at is not null
  from auth.users u
  where lower(u.email) = lower(p_email)
  limit 1;
$$;
revoke all on function public.auth_user_by_email(text) from public, anon, authenticated;
grant execute on function public.auth_user_by_email(text) to service_role;
