-- Client-facing RPCs for identity, discovery and chat reads. All functions
-- run as security definer with an empty search_path and check the caller.

create or replace function public.new_invite_code()
returns text language sql volatile set search_path = '' as $$
  select translate(encode(extensions.gen_random_bytes(12), 'base64'), '+/=', '-_');
$$;

create or replace function public.require_user()
returns uuid language plpgsql stable set search_path = '' as $$
declare v uuid := (select auth.uid());
begin
  if v is null then
    raise exception 'not_authenticated' using errcode = '28000';
  end if;
  return v;
end $$;

create or replace function public.post_system_message(p_conversation_id uuid, p_body jsonb, p_kind text default 'system', p_sender uuid default null)
returns uuid language plpgsql security definer set search_path = '' as $$
declare v_id uuid := gen_random_uuid();
begin
  insert into public.messages (id, conversation_id, sender_id, kind, system)
  values (v_id, p_conversation_id, p_sender, p_kind, p_body);
  update public.conversations c set last_message_at = now(), last_message_id = v_id where c.id = p_conversation_id;
  return v_id;
end $$;

create or replace function public.is_username_available(p_username text)
returns boolean language sql stable security definer set search_path = '' as $$
  select lower(coalesce(p_username, '')) ~ '^[a-z0-9_.]{3,24}$'
     and not exists (
       select 1 from public.profiles p
       where p.username = lower(p_username) and p.id <> (select auth.uid())
     );
$$;

create or replace function public.get_profiles(p_ids uuid[])
returns table (
  id uuid, username text, display_name text, about text, avatar_path text,
  avatar_version integer, is_contact boolean, blocked_by_me boolean
) language sql stable security definer set search_path = '' as $$
  select p.id, p.username, p.display_name,
         case when public.can_see_field(p.id, s.about) then p.about end,
         case when public.can_see_field(p.id, s.profile_photo) then p.avatar_path end,
         p.avatar_version,
         exists (select 1 from public.user_contacts c where c.owner_id = (select auth.uid()) and c.contact_id = p.id),
         exists (select 1 from public.user_blocks b where b.blocker_id = (select auth.uid()) and b.blocked_id = p.id)
  from public.profiles p
  left join public.user_privacy_settings s on s.user_id = p.id
  where (select auth.uid()) is not null and p.id = any (p_ids)
  limit 500;
$$;

create or replace function public.like_escape(p text)
returns text language sql immutable set search_path = '' as $$
  select replace(replace(replace(p, chr(92), chr(92) || chr(92)), '%', chr(92) || '%'), '_', chr(92) || '_');
$$;

create or replace function public.search_users(p_query text, p_limit integer default 20)
returns table (id uuid, username text, display_name text, avatar_path text, avatar_version integer, is_contact boolean)
language plpgsql stable security definer set search_path = '' as $$
declare
  v_me uuid := (select auth.uid());
  v_q text := ltrim(lower(trim(coalesce(p_query, ''))), '@');
  v_like text;
begin
  if v_me is null or char_length(v_q) < 2 then
    return;
  end if;
  v_like := public.like_escape(v_q);
  return query
  select p.id, p.username, p.display_name,
         case when public.can_see_field(p.id, s.profile_photo) then p.avatar_path end,
         p.avatar_version,
         exists (select 1 from public.user_contacts c where c.owner_id = v_me and c.contact_id = p.id)
  from public.profiles p
  join public.user_privacy_settings s on s.user_id = p.id
  where p.onboarded and p.id <> v_me
    and not public.is_blocked_between(p.id, v_me)
    and (p.username like v_like || '%'
         or (char_length(v_q) >= 3 and lower(p.display_name) like '%' || v_like || '%'))
  order by (p.username = v_q) desc, (p.username like v_like || '%') desc, p.display_name
  limit least(greatest(coalesce(p_limit, 20), 1), 50);
end $$;

-- Contact discovery: the client sends SHA-256 hashes of normalised phone
-- numbers; nothing is stored and only opted-in accounts match.
create or replace function public.match_contacts(p_hashes text[])
returns table (id uuid, phone_hash text, username text, display_name text, avatar_path text, avatar_version integer, is_contact boolean)
language sql stable security definer set search_path = '' as $$
  select p.id, p.phone_hash, p.username, p.display_name,
         case when public.can_see_field(p.id, s.profile_photo) then p.avatar_path end,
         p.avatar_version,
         exists (select 1 from public.user_contacts c where c.owner_id = (select auth.uid()) and c.contact_id = p.id)
  from public.profiles p
  join public.user_privacy_settings s on s.user_id = p.id and s.discoverable_by_phone
  where (select auth.uid()) is not null
    and coalesce(array_length(p_hashes, 1), 0) <= 5000
    and p.phone_hash = any (p_hashes)
    and p.onboarded and p.id <> (select auth.uid())
    and not public.is_blocked_between(p.id, (select auth.uid()));
$$;

create or replace function public.register_device(p_identity_key text, p_name text, p_platform text default 'android', p_app_version text default null)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_id uuid;
begin
  insert into public.user_devices (user_id, identity_key, name, platform, app_version)
  values (v_me, p_identity_key, left(coalesce(nullif(trim(p_name), ''), 'Android phone'), 64),
          coalesce(p_platform, 'android'), left(p_app_version, 32))
  on conflict (user_id, identity_key) do update
    set last_active_at = now(), name = excluded.name, app_version = excluded.app_version
  returning id into v_id;
  return v_id;
end $$;

create or replace function public.heartbeat(p_device_id uuid default null)
returns void language plpgsql security definer set search_path = '' as $$
declare v_me uuid := public.require_user();
begin
  update public.profiles p set last_seen_at = now()
  where p.id = v_me and (p.last_seen_at is null or p.last_seen_at < now() - interval '20 seconds');
  if p_device_id is not null then
    update public.user_devices d set last_active_at = now()
    where d.id = p_device_id and d.user_id = v_me and d.last_active_at < now() - interval '5 minutes';
  end if;
end $$;

-- Online / last seen, with WhatsApp-style reciprocity for last seen.
create or replace function public.get_presence(p_user_ids uuid[])
returns table (user_id uuid, online boolean, last_seen_at timestamptz)
language sql stable security definer set search_path = '' as $$
  with me as (
    select coalesce((select s.last_seen from public.user_privacy_settings s where s.user_id = (select auth.uid())), 'everyone') as my_last_seen
  )
  select p.id,
         coalesce(p.last_seen_at > now() - interval '75 seconds', false)
           and (s.online = 'everyone' or public.can_see_field(p.id, s.last_seen)),
         case when public.can_see_field(p.id, s.last_seen) and (select my_last_seen from me) <> 'nobody'
              then p.last_seen_at end
  from public.profiles p
  join public.user_privacy_settings s on s.user_id = p.id
  where (select auth.uid()) is not null
    and p.id = any (p_user_ids) and p.id <> (select auth.uid())
    and not public.is_blocked_between(p.id, (select auth.uid()))
    and public.shares_conversation(p.id, (select auth.uid()))
  limit 200;
$$;

create or replace function public.get_conversation_devices(p_conversation_id uuid)
returns table (user_id uuid, device_id uuid, identity_key text)
language sql stable security definer set search_path = '' as $$
  select d.user_id, d.id, d.identity_key
  from public.conversation_members m
  join public.user_devices d on d.user_id = m.user_id
  where m.conversation_id = p_conversation_id and public.is_member(p_conversation_id);
$$;

create or replace function public.get_or_create_direct(p_other uuid)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_key text;
  v_id uuid;
begin
  if p_other is null or p_other = v_me then
    raise exception 'invalid_user' using errcode = '22023';
  end if;
  if not exists (select 1 from public.profiles p where p.id = p_other) then
    raise exception 'user_not_found' using errcode = 'P0002';
  end if;
  v_key := public.direct_key(v_me, p_other);
  select c.id into v_id from public.conversations c where c.direct_key = v_key;
  if v_id is null then
    insert into public.conversations (type, direct_key, created_by)
    values ('direct', v_key, v_me)
    on conflict (direct_key) do nothing
    returning id into v_id;
    if v_id is null then
      select c.id into v_id from public.conversations c where c.direct_key = v_key;
    end if;
  end if;
  insert into public.conversation_members (conversation_id, user_id) values (v_id, v_me) on conflict do nothing;
  insert into public.conversation_members (conversation_id, user_id) values (v_id, p_other) on conflict do nothing;
  return v_id;
end $$;

create or replace function public.get_chat_list(p_device_id uuid default null)
returns table (
  conversation_id uuid, type text, title text, avatar_path text, avatar_version integer,
  other_user_id uuid, community_id uuid, is_announcement boolean, only_admins_send boolean,
  member_count integer, my_role text,
  last_message_id uuid, last_message_at timestamptz, last_kind text, last_sender_id uuid,
  last_deleted boolean, last_ciphertext text, last_nonce text, last_eph_key text,
  last_wrapped_key text, last_system jsonb, last_edited boolean,
  unread_count integer, muted_until timestamptz, archived boolean, pinned_at timestamptz,
  peer_delivered_up_to timestamptz, peer_read_up_to timestamptz, blocked_by_me boolean,
  created_at timestamptz
) language sql stable security definer set search_path = '' as $$
  with me as (
    select (select auth.uid()) as uid,
           coalesce((select s.read_receipts from public.user_privacy_settings s where s.user_id = (select auth.uid())), true) as rr,
           exists (select 1 from public.user_devices d where d.id = p_device_id and d.user_id = (select auth.uid())) as own_device
  ),
  mine as (
    select m.conversation_id, m.role, m.joined_at, st.last_read_at, st.muted_until, st.archived, st.pinned_at, st.cleared_at
    from public.conversation_members m
    join public.conversation_member_state st on st.conversation_id = m.conversation_id and st.user_id = m.user_id
    where m.user_id = (select uid from me)
  )
  select c.id, c.type,
         coalesce(g.name, nullif(op.display_name, ''), op.username, 'Deleted account'),
         case when c.type = 'group' then g.avatar_path
              when public.can_see_field(op.id, ops.profile_photo) then op.avatar_path end,
         coalesce(g.avatar_version, op.avatar_version, 0),
         other.user_id, c.community_id, coalesce(g.is_announcement, false), coalesce(g.only_admins_send, false),
         (select count(*)::int from public.conversation_members x where x.conversation_id = c.id),
         mine.role,
         lm.id, coalesce(lm.created_at, c.created_at), lm.kind, lm.sender_id, lm.deleted_at is not null,
         lm.ciphertext, lm.nonce, lm.eph_key,
         case when (select own_device from me) then lm.keys ->> p_device_id::text end,
         lm.system, lm.edited_at is not null,
         (select count(*)::int from (
            select 1 from public.messages u
            where u.conversation_id = c.id
              and u.created_at > greatest(coalesce(mine.last_read_at, mine.joined_at), coalesce(mine.cleared_at, '-infinity'::timestamptz))
              and u.created_at >= mine.joined_at
              and u.sender_id is distinct from (select uid from me)
              and u.deleted_at is null and u.kind <> 'system'
              and not u.hidden_for_recipients
            limit 999) q),
         mine.muted_until, mine.archived, mine.pinned_at,
         case when c.type = 'direct' then other.delivered_up_to
              else nullif((select min(coalesce(x.delivered_up_to, '-infinity'::timestamptz)) from public.conversation_members x
                           where x.conversation_id = c.id and x.user_id <> (select uid from me)), '-infinity'::timestamptz) end,
         case when not (select rr from me) then null
              when c.type = 'direct' then other.read_up_to
              else nullif((select min(coalesce(x.read_up_to, '-infinity'::timestamptz)) from public.conversation_members x
                           where x.conversation_id = c.id and x.user_id <> (select uid from me)), '-infinity'::timestamptz) end,
         coalesce(exists (select 1 from public.user_blocks b where b.blocker_id = (select uid from me) and b.blocked_id = other.user_id), false),
         c.created_at
  from mine
  join public.conversations c on c.id = mine.conversation_id
  left join public.groups g on g.conversation_id = c.id
  left join lateral (
    select x.user_id, x.delivered_up_to, x.read_up_to from public.conversation_members x
    where c.type = 'direct' and x.conversation_id = c.id and x.user_id <> (select uid from me)
    limit 1
  ) other on true
  left join public.profiles op on op.id = other.user_id
  left join public.user_privacy_settings ops on ops.user_id = other.user_id
  left join lateral (
    select m.* from public.messages m
    where m.conversation_id = c.id
      and m.created_at >= mine.joined_at
      and m.created_at > coalesce(mine.cleared_at, '-infinity'::timestamptz)
      and (not m.hidden_for_recipients or m.sender_id = (select uid from me))
      and not exists (select 1 from public.message_hidden h where h.user_id = (select uid from me) and h.message_id = m.id)
    order by m.created_at desc
    limit 1
  ) lm on true
  where c.type = 'group' or lm.id is not null
  order by mine.pinned_at desc nulls last, coalesce(lm.created_at, c.created_at) desc;
$$;

create or replace function public.get_messages(p_conversation_id uuid, p_device_id uuid default null, p_before timestamptz default null, p_limit integer default 50)
returns table (
  id uuid, conversation_id uuid, sender_id uuid, sender_device_id uuid, kind text,
  ciphertext text, nonce text, eph_key text, wrapped_key text, system jsonb,
  created_at timestamptz, updated_at timestamptz, edited_at timestamptz, deleted_at timestamptz
) language sql stable security definer set search_path = '' as $$
  with mine as (
    select m.joined_at, st.cleared_at,
           exists (select 1 from public.user_devices d where d.id = p_device_id and d.user_id = (select auth.uid())) as own_device
    from public.conversation_members m
    join public.conversation_member_state st on st.conversation_id = m.conversation_id and st.user_id = m.user_id
    where m.conversation_id = p_conversation_id and m.user_id = (select auth.uid())
  )
  select x.id, x.conversation_id, x.sender_id, x.sender_device_id, x.kind, x.ciphertext, x.nonce, x.eph_key,
         case when mine.own_device then x.keys ->> p_device_id::text end,
         x.system, x.created_at, x.updated_at, x.edited_at, x.deleted_at
  from mine
  join lateral (
    select m.* from public.messages m
    where m.conversation_id = p_conversation_id
      and m.created_at >= mine.joined_at
      and m.created_at > coalesce(mine.cleared_at, '-infinity'::timestamptz)
      and (p_before is null or m.created_at < p_before)
      and (not m.hidden_for_recipients or m.sender_id = (select auth.uid()))
      and not exists (select 1 from public.message_hidden h where h.user_id = (select auth.uid()) and h.message_id = m.id)
    order by m.created_at desc
    limit least(greatest(coalesce(p_limit, 50), 1), 200)
  ) x on true
  order by x.created_at desc;
$$;

-- Catch-up after being offline: everything created, edited or deleted since a cursor.
create or replace function public.sync_messages(p_device_id uuid, p_since timestamptz, p_limit integer default 300)
returns table (
  id uuid, conversation_id uuid, sender_id uuid, sender_device_id uuid, kind text,
  ciphertext text, nonce text, eph_key text, wrapped_key text, system jsonb,
  created_at timestamptz, updated_at timestamptz, edited_at timestamptz, deleted_at timestamptz
) language sql stable security definer set search_path = '' as $$
  select m.id, m.conversation_id, m.sender_id, m.sender_device_id, m.kind, m.ciphertext, m.nonce, m.eph_key,
         case when exists (select 1 from public.user_devices d where d.id = p_device_id and d.user_id = (select auth.uid()))
              then m.keys ->> p_device_id::text end,
         m.system, m.created_at, m.updated_at, m.edited_at, m.deleted_at
  from public.conversation_members cm
  join public.conversation_member_state st on st.conversation_id = cm.conversation_id and st.user_id = cm.user_id
  join public.messages m on m.conversation_id = cm.conversation_id
  where cm.user_id = (select auth.uid())
    and m.updated_at > coalesce(p_since, '-infinity'::timestamptz)
    and m.created_at >= cm.joined_at
    and m.created_at > coalesce(st.cleared_at, '-infinity'::timestamptz)
    and (not m.hidden_for_recipients or m.sender_id = (select auth.uid()))
    and not exists (select 1 from public.message_hidden h where h.user_id = (select auth.uid()) and h.message_id = m.id)
  order by m.updated_at asc
  limit least(greatest(coalesce(p_limit, 300), 1), 500);
$$;

create or replace function public.mark_delivered(p_conversation_id uuid, p_up_to timestamptz)
returns void language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_up timestamptz := least(p_up_to, now());
begin
  update public.conversation_members m set delivered_up_to = v_up
  where m.conversation_id = p_conversation_id and m.user_id = v_me
    and (m.delivered_up_to is null or m.delivered_up_to < v_up);
end $$;

create or replace function public.mark_all_delivered()
returns void language plpgsql security definer set search_path = '' as $$
declare v_me uuid := public.require_user();
begin
  update public.conversation_members m set delivered_up_to = c.last_message_at
  from public.conversations c
  where c.id = m.conversation_id and m.user_id = v_me and c.last_message_at is not null
    and (m.delivered_up_to is null or m.delivered_up_to < c.last_message_at);
end $$;

create or replace function public.mark_read(p_conversation_id uuid, p_up_to timestamptz)
returns void language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_up timestamptz := least(p_up_to, now());
  v_rr boolean;
begin
  update public.conversation_member_state st set last_read_at = v_up
  where st.conversation_id = p_conversation_id and st.user_id = v_me
    and (st.last_read_at is null or st.last_read_at < v_up);
  select coalesce(s.read_receipts, true) into v_rr from public.user_privacy_settings s where s.user_id = v_me;
  update public.conversation_members m
     set delivered_up_to = greatest(coalesce(m.delivered_up_to, '-infinity'::timestamptz), v_up),
         read_up_to = case when coalesce(v_rr, true) then greatest(coalesce(m.read_up_to, '-infinity'::timestamptz), v_up) else m.read_up_to end
   where m.conversation_id = p_conversation_id and m.user_id = v_me
     and (m.delivered_up_to is null or m.delivered_up_to < v_up
          or (coalesce(v_rr, true) and (m.read_up_to is null or m.read_up_to < v_up)));
end $$;
