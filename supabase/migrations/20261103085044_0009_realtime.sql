-- Realtime: every client listens on one private topic "user:<id>". Database
-- triggers push messages, receipts, reactions, membership and call events
-- there with realtime.send, so no client can read another user's stream.
-- Ephemeral topics: "conv:<id>" (typing), "presence:<user id>" (online),
-- "call:<id>" (WebRTC signalling) are authorised by the policies below.

create or replace function public.rt_send(p_user_id uuid, p_event text, p_payload jsonb)
returns void language plpgsql security definer set search_path = '' as $$
begin
  perform realtime.send(p_payload, p_event, 'user:' || p_user_id::text, true);
exception when others then
  raise warning 'hime realtime send failed: %', sqlerrm;
end $$;

create or replace function public.rt_send_to_members(p_conversation_id uuid, p_event text, p_payload jsonb, p_exclude uuid default null)
returns void language plpgsql security definer set search_path = '' as $$
declare r record;
begin
  for r in select m.user_id from public.conversation_members m
           where m.conversation_id = p_conversation_id and (p_exclude is null or m.user_id <> p_exclude) loop
    perform public.rt_send(r.user_id, p_event, p_payload);
  end loop;
end $$;

create or replace function public.rt_on_message()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  r record;
  v_keys jsonb;
begin
  for r in select m.user_id, m.joined_at from public.conversation_members m where m.conversation_id = new.conversation_id loop
    if r.joined_at > new.created_at then
      continue;
    end if;
    if new.hidden_for_recipients and r.user_id is distinct from new.sender_id then
      continue;
    end if;
    v_keys := null;
    if new.keys is not null then
      select jsonb_object_agg(d.id::text, new.keys -> d.id::text) into v_keys
      from public.user_devices d where d.user_id = r.user_id and new.keys ? d.id::text;
    end if;
    perform public.rt_send(r.user_id, 'message', jsonb_build_object(
      'op', lower(tg_op), 'id', new.id, 'conversation_id', new.conversation_id, 'sender_id', new.sender_id,
      'sender_device_id', new.sender_device_id, 'kind', new.kind, 'ciphertext', new.ciphertext,
      'nonce', new.nonce, 'eph_key', new.eph_key, 'keys', v_keys, 'system', new.system,
      'created_at', new.created_at, 'updated_at', new.updated_at, 'edited_at', new.edited_at,
      'deleted_at', new.deleted_at));
  end loop;
  return null;
end $$;
create trigger messages_realtime after insert or update on public.messages
for each row execute function public.rt_on_message();

create or replace function public.rt_on_member_change()
returns trigger language plpgsql security definer set search_path = '' as $$
declare v_conv uuid := coalesce(new.conversation_id, old.conversation_id);
begin
  if tg_op = 'UPDATE' then
    if new.delivered_up_to is distinct from old.delivered_up_to or new.read_up_to is distinct from old.read_up_to then
      perform public.rt_send_to_members(v_conv, 'receipt', jsonb_build_object(
        'conversation_id', v_conv, 'user_id', new.user_id,
        'delivered_up_to', new.delivered_up_to, 'read_up_to', new.read_up_to), new.user_id);
    end if;
    if new.role is distinct from old.role then
      perform public.rt_send_to_members(v_conv, 'conversation', jsonb_build_object('conversation_id', v_conv, 'reason', 'role'));
    end if;
    return null;
  end if;
  if not exists (select 1 from public.conversations c where c.id = v_conv) then
    if tg_op = 'DELETE' then
      perform public.rt_send(old.user_id, 'conversation', jsonb_build_object('conversation_id', v_conv, 'reason', 'deleted'));
    end if;
    return null;
  end if;
  perform public.rt_send_to_members(v_conv, 'conversation', jsonb_build_object('conversation_id', v_conv, 'reason', 'members'));
  if tg_op = 'DELETE' then
    perform public.rt_send(old.user_id, 'conversation', jsonb_build_object('conversation_id', v_conv, 'reason', 'removed'));
  end if;
  return null;
end $$;
create trigger conversation_members_realtime after insert or update or delete on public.conversation_members
for each row execute function public.rt_on_member_change();

create or replace function public.rt_on_group_change()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  perform public.rt_send_to_members(new.conversation_id, 'conversation',
    jsonb_build_object('conversation_id', new.conversation_id, 'reason', 'info'));
  return null;
end $$;
create trigger groups_realtime after update on public.groups
for each row execute function public.rt_on_group_change();

create or replace function public.rt_on_reaction()
returns trigger language plpgsql security definer set search_path = '' as $$
declare v record;
begin
  if tg_op = 'DELETE' then
    v := old;
  else
    v := new;
  end if;
  if not exists (select 1 from public.conversations c where c.id = v.conversation_id) then
    return null;
  end if;
  perform public.rt_send_to_members(v.conversation_id, 'reaction', jsonb_build_object(
    'conversation_id', v.conversation_id, 'message_id', v.message_id, 'user_id', v.user_id,
    'emoji', case when tg_op = 'DELETE' then null else new.emoji end));
  return null;
end $$;
create trigger message_reactions_realtime after insert or update or delete on public.message_reactions
for each row execute function public.rt_on_reaction();

create or replace function public.rt_on_pin()
returns trigger language plpgsql security definer set search_path = '' as $$
declare v_conv uuid := coalesce(new.conversation_id, old.conversation_id);
begin
  if exists (select 1 from public.conversations c where c.id = v_conv) then
    perform public.rt_send_to_members(v_conv, 'pins', jsonb_build_object('conversation_id', v_conv));
  end if;
  return null;
end $$;
create trigger conversation_pins_realtime after insert or delete on public.conversation_pins
for each row execute function public.rt_on_pin();

create or replace function public.call_event_payload(p_call_id uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'call_id', c.id, 'status', c.status, 'media', c.media, 'conversation_id', c.conversation_id,
    'caller_id', c.initiator_id,
    'caller_name', coalesce(nullif(p.display_name, ''), p.username, 'Hime user'),
    'created_at', c.created_at, 'answered_at', c.answered_at, 'ended_at', c.ended_at, 'end_reason', c.end_reason)
  from public.calls c left join public.profiles p on p.id = c.initiator_id
  where c.id = p_call_id;
$$;

create or replace function public.rt_on_call_participant()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if new.role = 'callee' and new.state = 'invited'
     and exists (select 1 from public.calls c where c.id = new.call_id and c.status = 'ringing') then
    perform public.rt_send(new.user_id, 'call', public.call_event_payload(new.call_id));
  end if;
  return null;
end $$;
create trigger call_participants_realtime after insert on public.call_participants
for each row execute function public.rt_on_call_participant();

create or replace function public.rt_on_call_change()
returns trigger language plpgsql security definer set search_path = '' as $$
declare r record;
begin
  for r in select p.user_id from public.call_participants p where p.call_id = new.id loop
    perform public.rt_send(r.user_id, 'call', public.call_event_payload(new.id));
  end loop;
  return null;
end $$;
create trigger calls_realtime after update of status on public.calls
for each row execute function public.rt_on_call_change();

-- Realtime authorisation policies ------------------------------------------------
create policy hime_realtime_receive on realtime.messages for select to authenticated
using (
  case split_part((select realtime.topic()), ':', 1)
    when 'user' then (select realtime.topic()) = 'user:' || (select auth.uid())::text
    when 'conv' then realtime.messages.extension in ('broadcast', 'presence')
      and public.try_uuid(split_part((select realtime.topic()), ':', 2)) in (select public.my_conversation_ids())
    when 'presence' then realtime.messages.extension = 'presence'
      and public.can_view_presence(split_part((select realtime.topic()), ':', 2))
    when 'call' then realtime.messages.extension = 'broadcast'
      and public.try_uuid(split_part((select realtime.topic()), ':', 2)) in (select public.my_call_ids())
    else false
  end
);

create policy hime_realtime_send on realtime.messages for insert to authenticated
with check (
  case split_part((select realtime.topic()), ':', 1)
    when 'conv' then realtime.messages.extension in ('broadcast', 'presence')
      and public.try_uuid(split_part((select realtime.topic()), ':', 2)) in (select public.my_conversation_ids())
    when 'presence' then realtime.messages.extension = 'presence'
      and split_part((select realtime.topic()), ':', 2) = (select auth.uid())::text
    when 'call' then realtime.messages.extension = 'broadcast'
      and public.try_uuid(split_part((select realtime.topic()), ':', 2)) in (select public.my_call_ids())
    else false
  end
);

-- Fix: call history filter (no-op clause removed).
create or replace function public.get_call_history(p_limit integer default 50, p_before timestamptz default null)
returns table (id uuid, conversation_id uuid, media text, status text, end_reason text, created_at timestamptz,
               answered_at timestamptz, ended_at timestamptz, outgoing boolean, peer_id uuid, peer_name text,
               peer_avatar_path text, peer_avatar_version integer, duration_seconds integer)
language sql stable security definer set search_path = '' as $$
  select c.id, c.conversation_id, c.media, c.status, c.end_reason, c.created_at, c.answered_at, c.ended_at,
         c.initiator_id = (select auth.uid()), peer.user_id,
         coalesce(nullif(pp.display_name, ''), pp.username, 'Deleted account'),
         case when public.can_see_field(pp.id, ps.profile_photo) then pp.avatar_path end,
         coalesce(pp.avatar_version, 0),
         case when c.answered_at is not null then extract(epoch from (coalesce(c.ended_at, now()) - c.answered_at))::int end
  from public.call_participants mine
  join public.calls c on c.id = mine.call_id
  left join lateral (select p.user_id from public.call_participants p where p.call_id = c.id and p.user_id <> mine.user_id limit 1) peer on true
  left join public.profiles pp on pp.id = peer.user_id
  left join public.user_privacy_settings ps on ps.user_id = peer.user_id
  where mine.user_id = (select auth.uid())
    and (p_before is null or c.created_at < p_before)
  order by c.created_at desc
  limit least(greatest(coalesce(p_limit, 50), 1), 200);
$$;
