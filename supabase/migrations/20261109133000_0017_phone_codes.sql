-- Phone-number sign-in with Hime's own 6-digit SMS codes (sent by the
-- phone-auth edge function). Only the service role can touch these.
create table if not exists public.auth_phone_codes (
  id bigint generated always as identity primary key,
  phone text not null,
  code_hash text not null,
  attempts int not null default 0,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_at timestamptz,
  ip text
);
create index if not exists auth_phone_codes_phone_idx on public.auth_phone_codes (phone, created_at desc);
alter table public.auth_phone_codes enable row level security;
revoke all on public.auth_phone_codes from public, anon, authenticated;

-- Account that owns a phone number (auth.users stores it as digits only).
create or replace function public.auth_user_by_phone(p_phone text)
returns table (id uuid, email text, phone_confirmed boolean)
language sql stable security definer set search_path = ''
as $$
  select u.id, u.email, u.phone_confirmed_at is not null
  from auth.users u
  where u.phone = regexp_replace(p_phone, '\D', '', 'g')
  limit 1;
$$;
revoke all on function public.auth_user_by_phone(text) from public, anon, authenticated;
grant execute on function public.auth_user_by_phone(text) to service_role;

-- Defaults for the SMS sender (see the phone-auth function); the gateway
-- username/password are added separately once the SMS phone is set up.
insert into public.app_secrets (key, value) values
  ('sms_gateway_url', 'https://api.sms-gate.app/3rdparty/v1'),
  ('sms_allowed_prefixes', '+91'),
  ('sms_daily_cap', '90')
on conflict (key) do nothing;
