-- Chat list including the last message's sender device (needed to decrypt
-- previews on a fresh install).
create or replace function public.get_chats(p_device_id uuid default null)
returns table (
  conversation_id uuid, type text, title text, avatar_path text, avatar_version integer,
  other_user_id uuid, community_id uuid, is_announcement boolean, only_admins_send boolean,
  member_count integer, my_role text,
  last_message_id uuid, last_message_at timestamptz, last_kind text, last_sender_id uuid,
  last_sender_device_id uuid, last_deleted boolean, last_ciphertext text, last_nonce text, last_eph_key text,
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
         lm.id, coalesce(lm.created_at, c.created_at), lm.kind, lm.sender_id, lm.sender_device_id,
         lm.deleted_at is not null, lm.ciphertext, lm.nonce, lm.eph_key,
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
revoke all on function public.get_chats(uuid) from public, anon;
grant execute on function public.get_chats(uuid) to authenticated, service_role;
