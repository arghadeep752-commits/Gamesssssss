-- Soft-deleted attachments: the row keeps bookkeeping until the cleanup job
-- has removed the encrypted blob from storage.
alter table public.attachments add column deleted_at timestamptz;
create index attachments_deleted_idx on public.attachments (deleted_at) where deleted_at is not null;

create or replace function public.on_attachment_soft_deleted()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if old.deleted_at is null and new.deleted_at is not null then
    perform public.queue_storage_delete('media', new.path);
  end if;
  return null;
end $$;
create trigger attachments_soft_deleted after update of deleted_at on public.attachments
for each row execute function public.on_attachment_soft_deleted();

-- Delete for everyone: wipes ciphertext and keys, leaving only a tombstone.
create or replace function public.delete_message_for_everyone(p_id uuid)
returns void language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_msg record;
  v_role text;
  v_type text;
begin
  select m.* into v_msg from public.messages m where m.id = p_id;
  if not found or v_msg.deleted_at is not null then
    return;
  end if;
  if v_msg.kind in ('system', 'call') then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  select m.role into v_role from public.conversation_members m where m.conversation_id = v_msg.conversation_id and m.user_id = v_me;
  select c.type into v_type from public.conversations c where c.id = v_msg.conversation_id;
  if v_role is null then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  if v_msg.sender_id = v_me then
    if v_msg.created_at < now() - interval '2 days' then
      raise exception 'delete_window_expired' using errcode = '22023';
    end if;
  elsif not (v_type = 'group' and v_role in ('owner', 'admin')) then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  update public.messages m
     set ciphertext = null, nonce = null, eph_key = null, keys = null,
         system = jsonb_build_object('deleted_by', v_me),
         deleted_at = now(), updated_at = now()
   where m.id = p_id;
  update public.attachments a set deleted_at = now() where a.message_id = p_id and a.deleted_at is null;
end $$;

-- Pinned messages: members pin/unpin directly (RLS), at most three per chat.
create or replace function public.can_pin(p_conversation_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.conversation_members m
    left join public.groups g on g.conversation_id = m.conversation_id
    where m.conversation_id = p_conversation_id and m.user_id = (select auth.uid())
      and (g.conversation_id is null or not g.only_admins_edit_info or m.role in ('owner', 'admin'))
  );
$$;

create or replace function public.enforce_pin_limit()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if (select count(*) from public.conversation_pins p where p.conversation_id = new.conversation_id) >= 3 then
    raise exception 'pin_limit_reached' using errcode = '23514';
  end if;
  if not exists (select 1 from public.messages m where m.id = new.message_id and m.conversation_id = new.conversation_id and m.deleted_at is null) then
    raise exception 'message_not_found' using errcode = 'P0002';
  end if;
  return new;
end $$;
create trigger conversation_pins_limit before insert on public.conversation_pins
for each row execute function public.enforce_pin_limit();

create policy pins_insert_member on public.conversation_pins for insert to authenticated
  with check (pinned_by = (select auth.uid()) and public.can_pin(conversation_id));
create policy pins_delete_member on public.conversation_pins for delete to authenticated
  using (public.can_pin(conversation_id));
grant insert (conversation_id, message_id, pinned_by), delete on public.conversation_pins to authenticated;

-- Leaving / removing group members happens through RLS-checked deletes.
create or replace function public.can_remove_member(p_conversation_id uuid, p_user_id uuid, p_role text)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.conversations c
    join public.conversation_members me on me.conversation_id = c.id and me.user_id = (select auth.uid())
    where c.id = p_conversation_id and c.type = 'group'
      and (p_user_id = (select auth.uid())
           or (me.role = 'owner')
           or (me.role = 'admin' and p_role <> 'owner'))
  );
$$;

create policy members_delete_allowed on public.conversation_members for delete to authenticated
  using (public.can_remove_member(conversation_id, user_id, role));
grant delete on public.conversation_members to authenticated;

create or replace function public.on_member_removed_notice()
returns trigger language plpgsql security definer set search_path = '' as $$
declare v_actor uuid := (select auth.uid());
begin
  if not exists (select 1 from public.conversations c where c.id = old.conversation_id and c.type = 'group') then
    return null;
  end if;
  if not exists (select 1 from public.conversation_members m where m.conversation_id = old.conversation_id) then
    return null;
  end if;
  perform public.post_system_message(old.conversation_id,
    case when v_actor is null or v_actor = old.user_id
         then jsonb_build_object('type', 'member_left', 'actor', old.user_id)
         else jsonb_build_object('type', 'member_removed', 'actor', v_actor, 'targets', jsonb_build_array(old.user_id)) end);
  return null;
end $$;
create trigger conversation_members_removed_notice after delete on public.conversation_members
for each row execute function public.on_member_removed_notice();

-- Group owners can delete the whole group (cascades to messages and media).
create policy conversations_delete_owner on public.conversations for delete to authenticated
  using (type = 'group' and public.member_role(id) = 'owner');
grant delete on public.conversations to authenticated;

-- Communities: members leave by deleting their own membership; owners delete.
create policy community_members_delete_own on public.community_members for delete to authenticated
  using (user_id = (select auth.uid()));
grant delete on public.community_members to authenticated;
create policy communities_delete_owner on public.communities for delete to authenticated
  using (public.community_role(id) = 'owner');
grant delete on public.communities to authenticated;

create or replace function public.on_community_member_removed()
returns trigger language plpgsql security definer set search_path = '' as $$
declare v_next uuid;
begin
  if not exists (select 1 from public.communities c where c.id = old.community_id) then
    return null;
  end if;
  if not exists (select 1 from public.community_members m where m.community_id = old.community_id and m.role in ('owner', 'admin')) then
    select m.user_id into v_next from public.community_members m
    where m.community_id = old.community_id order by m.joined_at asc limit 1;
    if v_next is not null then
      update public.community_members m set role = 'owner'
      where m.community_id = old.community_id and m.user_id = v_next;
    end if;
  end if;
  return null;
end $$;
create trigger community_members_removed after delete on public.community_members
for each row execute function public.on_community_member_removed();
