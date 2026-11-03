-- Validates and stores an encrypted message. Idempotent on the client id so
-- retries from the offline queue never duplicate messages.
create or replace function public.send_message(
  p_id uuid, p_conversation_id uuid, p_kind text, p_ciphertext text, p_nonce text,
  p_eph_key text, p_keys jsonb, p_device_id uuid, p_attachments jsonb default '[]'::jsonb
) returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_existing record;
  v_type text;
  v_role text;
  v_group record;
  v_other uuid;
  v_hidden boolean := false;
  v_missing jsonb;
  v_keys jsonb;
  v_att jsonb;
  v_path text;
  v_size bigint;
  v_created timestamptz;
begin
  if p_kind not in ('text', 'image', 'video', 'voice', 'audio', 'document', 'contact', 'location') then
    raise exception 'invalid_kind' using errcode = '22023';
  end if;
  select m.id, m.sender_id, m.conversation_id, m.created_at into v_existing from public.messages m where m.id = p_id;
  if found then
    if v_existing.sender_id = v_me and v_existing.conversation_id = p_conversation_id then
      return jsonb_build_object('id', v_existing.id, 'created_at', v_existing.created_at, 'duplicate', true);
    end if;
    raise exception 'id_conflict' using errcode = '23505';
  end if;

  select m.role into v_role from public.conversation_members m
  where m.conversation_id = p_conversation_id and m.user_id = v_me;
  if v_role is null then
    raise exception 'not_a_member' using errcode = '42501';
  end if;
  if not exists (select 1 from public.user_devices d where d.id = p_device_id and d.user_id = v_me) then
    raise exception 'unknown_device' using errcode = '42501';
  end if;

  select c.type into v_type from public.conversations c where c.id = p_conversation_id;
  if v_type = 'group' then
    select g.only_admins_send, g.is_announcement into v_group from public.groups g where g.conversation_id = p_conversation_id;
    if (v_group.only_admins_send or v_group.is_announcement) and v_role not in ('owner', 'admin') then
      raise exception 'only_admins_can_send' using errcode = '42501';
    end if;
  else
    select m.user_id into v_other from public.conversation_members m
    where m.conversation_id = p_conversation_id and m.user_id <> v_me limit 1;
    if v_other is null then
      raise exception 'recipient_unavailable' using errcode = 'P0002';
    end if;
    if exists (select 1 from public.user_blocks b where b.blocker_id = v_me and b.blocked_id = v_other) then
      raise exception 'you_blocked_this_contact' using errcode = '42501';
    end if;
    -- Messages to someone who blocked the sender are kept for the sender only.
    v_hidden := exists (select 1 from public.user_blocks b where b.blocker_id = v_other and b.blocked_id = v_me);
  end if;

  if (select count(*) from public.messages m where m.sender_id = v_me and m.created_at > now() - interval '1 minute') >= 90 then
    raise exception 'rate_limited' using errcode = '54000';
  end if;

  select coalesce(jsonb_agg(d.id), '[]'::jsonb) into v_missing
  from public.conversation_members m join public.user_devices d on d.user_id = m.user_id
  where m.conversation_id = p_conversation_id and not (coalesce(p_keys, '{}'::jsonb) ? d.id::text);
  if jsonb_array_length(v_missing) > 0 then
    raise exception 'stale_devices' using errcode = 'P0001', detail = v_missing::text;
  end if;
  select coalesce(jsonb_object_agg(d.id::text, p_keys -> d.id::text), '{}'::jsonb) into v_keys
  from public.conversation_members m join public.user_devices d on d.user_id = m.user_id
  where m.conversation_id = p_conversation_id;

  insert into public.messages (id, conversation_id, sender_id, sender_device_id, kind, ciphertext, nonce, eph_key, keys, hidden_for_recipients)
  values (p_id, p_conversation_id, v_me, p_device_id, p_kind, p_ciphertext, p_nonce, p_eph_key, v_keys, v_hidden)
  returning created_at into v_created;

  for v_att in select value from jsonb_array_elements(coalesce(p_attachments, '[]'::jsonb)) loop
    v_path := v_att ->> 'path';
    if v_path is null or v_path not like p_conversation_id::text || '/%' then
      raise exception 'invalid_attachment' using errcode = '22023';
    end if;
    select (o.metadata ->> 'size')::bigint into v_size from storage.objects o
    where o.bucket_id = 'media' and o.name = v_path and o.owner_id = v_me::text;
    if v_size is null then
      raise exception 'attachment_not_uploaded' using errcode = '22023';
    end if;
    insert into public.attachments (conversation_id, message_id, uploader_id, path, kind, size_bytes)
    values (p_conversation_id, p_id, v_me, v_path,
            case when v_att ->> 'kind' in ('image', 'video', 'voice', 'audio', 'document') then v_att ->> 'kind' else 'document' end,
            greatest(v_size, 1))
    on conflict (path) do nothing;
  end loop;

  update public.conversation_members m set engaged = true
  where m.conversation_id = p_conversation_id and m.user_id = v_me and not m.engaged;
  if not v_hidden then
    update public.conversations c set last_message_at = v_created, last_message_id = p_id where c.id = p_conversation_id;
  end if;
  return jsonb_build_object('id', p_id, 'created_at', v_created, 'duplicate', false);
end $$;

create or replace function public.edit_message(p_id uuid, p_ciphertext text, p_nonce text, p_eph_key text, p_keys jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_msg record;
  v_missing jsonb;
  v_keys jsonb;
begin
  select m.* into v_msg from public.messages m where m.id = p_id;
  if not found or v_msg.sender_id is distinct from v_me then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  if v_msg.deleted_at is not null or v_msg.kind <> 'text' then
    raise exception 'not_editable' using errcode = '22023';
  end if;
  if v_msg.created_at < now() - interval '15 minutes' then
    raise exception 'edit_window_expired' using errcode = '22023';
  end if;
  select coalesce(jsonb_agg(d.id), '[]'::jsonb) into v_missing
  from public.conversation_members m join public.user_devices d on d.user_id = m.user_id
  where m.conversation_id = v_msg.conversation_id and not (coalesce(p_keys, '{}'::jsonb) ? d.id::text);
  if jsonb_array_length(v_missing) > 0 then
    raise exception 'stale_devices' using errcode = 'P0001', detail = v_missing::text;
  end if;
  select coalesce(jsonb_object_agg(d.id::text, p_keys -> d.id::text), '{}'::jsonb) into v_keys
  from public.conversation_members m join public.user_devices d on d.user_id = m.user_id
  where m.conversation_id = v_msg.conversation_id;
  update public.messages m
     set ciphertext = p_ciphertext, nonce = p_nonce, eph_key = p_eph_key, keys = v_keys,
         edited_at = now(), updated_at = now()
   where m.id = p_id;
  return jsonb_build_object('id', p_id, 'edited_at', now());
end $$;
