create or replace function public.register_push_token(p_token text, p_device_id uuid, p_platform text default 'android')
returns void language plpgsql security definer set search_path = '' as $$
declare v_me uuid := public.require_user();
begin
  if not exists (select 1 from public.user_devices d where d.id = p_device_id and d.user_id = v_me) then
    raise exception 'unknown_device' using errcode = '42501';
  end if;
  insert into public.notification_tokens (token, user_id, device_id, platform)
  values (p_token, v_me, p_device_id, coalesce(p_platform, 'android'))
  on conflict (token) do update
    set user_id = excluded.user_id, device_id = excluded.device_id, platform = excluded.platform, updated_at = now();
end $$;
