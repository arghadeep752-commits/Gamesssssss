-- Calls ---------------------------------------------------------------------
create or replace function public.expire_stale_calls()
returns void language plpgsql security definer set search_path = '' as $$
begin
  update public.calls c set status = 'missed', ended_at = now(), end_reason = 'no_answer'
  where c.status = 'ringing' and c.created_at < now() - interval '75 seconds';
  update public.calls c set status = 'ended', ended_at = now(), end_reason = 'stale'
  where c.status = 'active' and c.created_at < now() - interval '6 hours';
end $$;

create or replace function public.start_call(p_conversation_id uuid, p_media text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_type text;
  v_other uuid;
  v_id uuid;
  v_status text := 'ringing';
  v_reason text;
  v_callee_state text := 'invited';
begin
  if p_media not in ('audio', 'video') then
    raise exception 'invalid_media' using errcode = '22023';
  end if;
  select c.type into v_type from public.conversations c where c.id = p_conversation_id;
  if v_type is null or not public.is_member(p_conversation_id) then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  if v_type <> 'direct' then
    raise exception 'group_calls_not_supported' using errcode = '0A000';
  end if;
  select m.user_id into v_other from public.conversation_members m
  where m.conversation_id = p_conversation_id and m.user_id <> v_me limit 1;
  if v_other is null then
    raise exception 'recipient_unavailable' using errcode = 'P0002';
  end if;
  if public.is_blocked_between(v_me, v_other) then
    raise exception 'cannot_call' using errcode = '42501';
  end if;
  perform public.expire_stale_calls();
  if exists (
    select 1 from public.call_participants p join public.calls c on c.id = p.call_id
    where p.user_id = v_me and c.status in ('ringing', 'active') and p.state in ('invited', 'joined')
  ) then
    raise exception 'already_in_call' using errcode = '55000';
  end if;
  if exists (select 1 from public.user_privacy_settings s where s.user_id = v_other and s.calls_from = 'contacts')
     and not public.is_contact(v_other, v_me) then
    v_status := 'missed'; v_reason := 'silenced'; v_callee_state := 'missed';
  elsif exists (
    select 1 from public.call_participants p join public.calls c on c.id = p.call_id
    where p.user_id = v_other and c.status in ('ringing', 'active') and p.state in ('invited', 'joined')
  ) then
    v_status := 'busy'; v_reason := 'busy'; v_callee_state := 'busy';
  end if;
  insert into public.calls (conversation_id, initiator_id, media, status, end_reason, ended_at)
  values (p_conversation_id, v_me, p_media, v_status, v_reason, case when v_status <> 'ringing' then now() end)
  returning id into v_id;
  insert into public.call_participants (call_id, user_id, role, state, joined_at)
  values (v_id, v_me, 'caller', 'joined', now()), (v_id, v_other, 'callee', v_callee_state, null);
  return jsonb_build_object('id', v_id, 'status', v_status, 'reason', v_reason, 'media', p_media,
                            'conversation_id', p_conversation_id, 'peer_id', v_other, 'created_at', now());
end $$;

create or replace function public.answer_call(p_call_id uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_me uuid := public.require_user(); v_ok boolean;
begin
  update public.calls c set status = 'active', answered_at = now()
  where c.id = p_call_id and c.status = 'ringing'
    and exists (select 1 from public.call_participants p where p.call_id = c.id and p.user_id = v_me and p.role = 'callee')
  returning true into v_ok;
  if not coalesce(v_ok, false) then
    raise exception 'call_not_ringing' using errcode = '55000';
  end if;
  update public.call_participants p set state = 'joined', joined_at = now()
  where p.call_id = p_call_id and p.user_id = v_me;
  return jsonb_build_object('id', p_call_id, 'status', 'active', 'answered_at', now());
end $$;

create or replace function public.end_call(p_call_id uuid, p_reason text default 'hangup')
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_call record;
  v_role text;
  v_status text;
begin
  select p.role into v_role from public.call_participants p where p.call_id = p_call_id and p.user_id = v_me;
  if v_role is null then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  select c.* into v_call from public.calls c where c.id = p_call_id for update;
  if v_call.status = 'ringing' then
    v_status := case when v_role = 'callee' then 'declined'
                     when p_reason = 'no_answer' then 'missed'
                     when p_reason = 'failed' then 'failed'
                     else 'cancelled' end;
  elsif v_call.status = 'active' then
    v_status := case when p_reason = 'failed' then 'failed' else 'ended' end;
  else
    return jsonb_build_object('id', p_call_id, 'status', v_call.status);
  end if;
  update public.calls c set status = v_status, ended_at = now(), end_reason = left(coalesce(p_reason, ''), 32)
  where c.id = p_call_id;
  update public.call_participants p
     set state = case when p.state = 'invited' then case when v_status = 'declined' then 'declined' else 'missed' end
                      when p.state = 'joined' then 'left' else p.state end,
         left_at = now()
   where p.call_id = p_call_id;
  return jsonb_build_object('id', p_call_id, 'status', v_status);
end $$;

create or replace function public.get_call(p_call_id uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object('id', c.id, 'conversation_id', c.conversation_id, 'media', c.media, 'status', c.status,
    'initiator_id', c.initiator_id, 'created_at', c.created_at, 'answered_at', c.answered_at, 'ended_at', c.ended_at,
    'end_reason', c.end_reason,
    'peer_id', (select p.user_id from public.call_participants p where p.call_id = c.id and p.user_id <> (select auth.uid()) limit 1))
  from public.calls c
  where c.id = p_call_id
    and exists (select 1 from public.call_participants p where p.call_id = c.id and p.user_id = (select auth.uid()));
$$;

create or replace function public.get_incoming_call()
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object('id', c.id, 'conversation_id', c.conversation_id, 'media', c.media, 'status', c.status,
                            'initiator_id', c.initiator_id, 'created_at', c.created_at, 'peer_id', c.initiator_id)
  from public.call_participants p join public.calls c on c.id = p.call_id
  where p.user_id = (select auth.uid()) and p.role = 'callee' and p.state = 'invited'
    and c.status = 'ringing' and c.created_at > now() - interval '75 seconds'
  order by c.created_at desc limit 1;
$$;

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
    and not (mine.role = 'callee' and c.end_reason = 'silenced' and false)
  order by c.created_at desc
  limit least(greatest(coalesce(p_limit, 50), 1), 200);
$$;

-- Logs a call event into the chat timeline when a call reaches a final state.
create or replace function public.log_call_event()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if new.status in ('ringing', 'active') or new.conversation_id is null then
    return null;
  end if;
  if tg_op = 'UPDATE' and old.status not in ('ringing', 'active') then
    return null;
  end if;
  perform public.post_system_message(new.conversation_id,
    jsonb_build_object('call_id', new.id, 'media', new.media, 'status', new.status, 'reason', new.end_reason,
                       'initiator_id', new.initiator_id,
                       'duration', case when new.answered_at is not null
                                        then extract(epoch from (coalesce(new.ended_at, now()) - new.answered_at))::int else 0 end),
    'call', new.initiator_id);
  return null;
end $$;
create trigger calls_log_event after insert or update of status on public.calls
for each row execute function public.log_call_event();

-- Statuses ---------------------------------------------------------------------
create or replace function public.get_status_feed()
returns table (user_id uuid, display_name text, avatar_path text, avatar_version integer, muted boolean,
               latest_at timestamptz, all_viewed boolean, statuses jsonb)
language sql stable security definer set search_path = '' as $$
  select p.id, coalesce(nullif(p.display_name, ''), p.username, 'Hime user'),
         case when public.can_see_field(p.id, ps.profile_photo) then p.avatar_path end,
         p.avatar_version,
         exists (select 1 from public.status_mutes sm where sm.user_id = (select auth.uid()) and sm.muted_user_id = p.id),
         max(s.created_at),
         bool_and(exists (select 1 from public.status_views v where v.status_id = s.id and v.viewer_id = (select auth.uid()))),
         jsonb_agg(jsonb_build_object(
           'id', s.id, 'kind', s.kind, 'body', s.body, 'background', s.background, 'font', s.font,
           'media_path', s.media_path, 'caption', s.caption, 'duration_ms', s.duration_ms,
           'created_at', s.created_at, 'expires_at', s.expires_at,
           'viewed', exists (select 1 from public.status_views v where v.status_id = s.id and v.viewer_id = (select auth.uid())))
           order by s.created_at)
  from public.statuses s
  join public.profiles p on p.id = s.user_id
  left join public.user_privacy_settings ps on ps.user_id = p.id
  where (select auth.uid()) is not null
    and s.expires_at > now() and s.user_id <> (select auth.uid())
    and public.can_view_status(s.user_id)
  group by p.id, ps.profile_photo
  order by max(s.created_at) desc;
$$;

create or replace function public.get_status_viewers(p_status_id uuid)
returns table (viewer_id uuid, display_name text, avatar_path text, avatar_version integer, viewed_at timestamptz, reaction text)
language sql stable security definer set search_path = '' as $$
  select v.viewer_id, coalesce(nullif(p.display_name, ''), p.username, 'Hime user'),
         case when public.can_see_field(p.id, ps.profile_photo) then p.avatar_path end,
         p.avatar_version, v.viewed_at, v.reaction
  from public.status_views v
  join public.statuses s on s.id = v.status_id and s.user_id = (select auth.uid())
  join public.profiles p on p.id = v.viewer_id
  left join public.user_privacy_settings ps on ps.user_id = p.id
  where v.status_id = p_status_id
    and coalesce(ps.read_receipts, true)
  order by v.viewed_at desc;
$$;

create or replace function public.mark_status_viewed(p_status_id uuid, p_reaction text default null)
returns void language plpgsql security definer set search_path = '' as $$
declare v_me uuid := public.require_user();
begin
  if not exists (
    select 1 from public.statuses s
    where s.id = p_status_id and s.expires_at > now() and s.user_id <> v_me and public.can_view_status(s.user_id)
  ) then
    return;
  end if;
  insert into public.status_views (status_id, viewer_id, reaction)
  values (p_status_id, v_me, left(p_reaction, 16))
  on conflict (status_id, viewer_id) do update
    set reaction = coalesce(left(excluded.reaction, 16), public.status_views.reaction);
end $$;

-- Account -------------------------------------------------------------------------
create or replace function public.export_my_data()
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'generated_at', now(),
    'profile', (select jsonb_build_object('id', p.id, 'username', p.username, 'display_name', p.display_name,
                       'about', p.about, 'has_avatar', p.avatar_path is not null, 'created_at', p.created_at,
                       'last_seen_at', p.last_seen_at)
                from public.profiles p where p.id = (select auth.uid())),
    'privacy_settings', (select to_jsonb(s) - 'user_id' from public.user_privacy_settings s where s.user_id = (select auth.uid())),
    'notification_settings', (select to_jsonb(n) - 'user_id' from public.user_notification_settings n where n.user_id = (select auth.uid())),
    'devices', coalesce((select jsonb_agg(jsonb_build_object('name', d.name, 'platform', d.platform, 'created_at', d.created_at, 'last_active_at', d.last_active_at))
                from public.user_devices d where d.user_id = (select auth.uid())), '[]'::jsonb),
    'contacts', coalesce((select jsonb_agg(jsonb_build_object('user_id', c.contact_id, 'name', p.display_name, 'added_at', c.created_at))
                from public.user_contacts c join public.profiles p on p.id = c.contact_id where c.owner_id = (select auth.uid())), '[]'::jsonb),
    'blocked', coalesce((select jsonb_agg(jsonb_build_object('user_id', b.blocked_id, 'blocked_at', b.created_at))
                from public.user_blocks b where b.blocker_id = (select auth.uid())), '[]'::jsonb),
    'groups', coalesce((select jsonb_agg(jsonb_build_object('name', g.name, 'role', m.role, 'joined_at', m.joined_at))
                from public.conversation_members m join public.groups g on g.conversation_id = m.conversation_id
                where m.user_id = (select auth.uid())), '[]'::jsonb),
    'communities', coalesce((select jsonb_agg(jsonb_build_object('name', c.name, 'role', cm.role, 'joined_at', cm.joined_at))
                from public.community_members cm join public.communities c on c.id = cm.community_id
                where cm.user_id = (select auth.uid())), '[]'::jsonb),
    'calls', coalesce((select jsonb_agg(jsonb_build_object('media', c.media, 'status', c.status, 'created_at', c.created_at,
                                                             'answered_at', c.answered_at, 'ended_at', c.ended_at))
                from public.call_participants p join public.calls c on c.id = p.call_id where p.user_id = (select auth.uid())), '[]'::jsonb),
    'active_statuses', coalesce((select jsonb_agg(jsonb_build_object('kind', s.kind, 'created_at', s.created_at, 'expires_at', s.expires_at))
                from public.statuses s where s.user_id = (select auth.uid()) and s.expires_at > now()), '[]'::jsonb),
    'note', 'Message contents are end-to-end encrypted and cannot be exported by the server. Use "Export chat" inside a conversation to save messages from this device.'
  )
  where (select auth.uid()) is not null;
$$;
