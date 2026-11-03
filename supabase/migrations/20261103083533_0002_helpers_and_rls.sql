-- Membership flag used for the "contacts" privacy level: a direct chat only
-- makes you someone's contact once that person has written to you.
alter table public.conversation_members add column engaged boolean not null default false;

create or replace function public.try_uuid(p text)
returns uuid language plpgsql immutable set search_path = '' as $$
begin
  return p::uuid;
exception when others then
  return null;
end $$;

create or replace function public.my_conversation_ids()
returns setof uuid language sql stable security definer set search_path = '' as $$
  select m.conversation_id from public.conversation_members m where m.user_id = (select auth.uid());
$$;

create or replace function public.my_call_ids()
returns setof uuid language sql stable security definer set search_path = '' as $$
  select p.call_id from public.call_participants p where p.user_id = (select auth.uid());
$$;

create or replace function public.my_community_ids()
returns setof uuid language sql stable security definer set search_path = '' as $$
  select c.community_id from public.community_members c where c.user_id = (select auth.uid());
$$;

create or replace function public.is_member(p_conversation_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.conversation_members m
    where m.conversation_id = p_conversation_id and m.user_id = (select auth.uid())
  );
$$;

create or replace function public.member_role(p_conversation_id uuid)
returns text language sql stable security definer set search_path = '' as $$
  select m.role from public.conversation_members m
  where m.conversation_id = p_conversation_id and m.user_id = (select auth.uid());
$$;

create or replace function public.community_role(p_community_id uuid)
returns text language sql stable security definer set search_path = '' as $$
  select c.role from public.community_members c
  where c.community_id = p_community_id and c.user_id = (select auth.uid());
$$;

create or replace function public.is_blocked_between(p_a uuid, p_b uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.user_blocks b
    where (b.blocker_id = p_a and b.blocked_id = p_b) or (b.blocker_id = p_b and b.blocked_id = p_a)
  );
$$;

create or replace function public.direct_key(p_a uuid, p_b uuid)
returns text language sql immutable set search_path = '' as $$
  select least(p_a::text, p_b::text) || ':' || greatest(p_a::text, p_b::text);
$$;

create or replace function public.shares_conversation(p_a uuid, p_b uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.conversation_members a
    join public.conversation_members b on b.conversation_id = a.conversation_id and b.user_id = p_b
    where a.user_id = p_a
  );
$$;

-- Does p_owner treat p_other as a contact? (saved contact, or a direct chat
-- in which p_owner has written).
create or replace function public.is_contact(p_owner uuid, p_other uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.user_contacts c where c.owner_id = p_owner and c.contact_id = p_other)
      or exists (
        select 1 from public.conversations c
        join public.conversation_members m on m.conversation_id = c.id and m.user_id = p_owner and m.engaged
        where c.direct_key = public.direct_key(p_owner, p_other)
      );
$$;

-- Applies an everyone/contacts/nobody privacy level for the current viewer.
create or replace function public.can_see_field(p_owner uuid, p_level text)
returns boolean language sql stable security definer set search_path = '' as $$
  select p_owner = (select auth.uid())
    or (
      not exists (select 1 from public.user_blocks b where b.blocker_id = p_owner and b.blocked_id = (select auth.uid()))
      and case p_level
            when 'everyone' then true
            when 'contacts' then public.is_contact(p_owner, (select auth.uid()))
            else false
          end
    );
$$;

create or replace function public.can_view_avatar(p_owner text)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.user_privacy_settings s
    where s.user_id = public.try_uuid(p_owner) and public.can_see_field(s.user_id, s.profile_photo)
  );
$$;

create or replace function public.can_view_status(p_owner uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select p_owner = (select auth.uid()) or (
    not public.is_blocked_between(p_owner, (select auth.uid()))
    and exists (
      select 1 from public.user_privacy_settings s
      where s.user_id = p_owner and (
        (s.status_audience = 'contacts' and public.is_contact(p_owner, (select auth.uid())))
        or (s.status_audience = 'contacts_except' and public.is_contact(p_owner, (select auth.uid()))
            and not exists (select 1 from public.status_audience_list l
                            where l.user_id = p_owner and l.list_kind = 'except' and l.member_id = (select auth.uid())))
        or (s.status_audience = 'only_share_with'
            and exists (select 1 from public.status_audience_list l
                        where l.user_id = p_owner and l.list_kind = 'only' and l.member_id = (select auth.uid())))
      )
    )
  );
$$;

-- Presence topics ("presence:<user id>") may be watched by people who share a
-- conversation with the user, unless blocked or hidden by privacy settings.
create or replace function public.can_view_presence(p_owner text)
returns boolean language sql stable security definer set search_path = '' as $$
  select case when public.try_uuid(p_owner) = (select auth.uid()) then true else exists (
    select 1 from public.user_privacy_settings s
    where s.user_id = public.try_uuid(p_owner)
      and not public.is_blocked_between(s.user_id, (select auth.uid()))
      and public.shares_conversation(s.user_id, (select auth.uid()))
      and (s.online = 'everyone' or public.can_see_field(s.user_id, s.last_seen))
  ) end;
$$;

create or replace function public.can_edit_group_info(p_conversation_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.conversation_members m
    join public.groups g on g.conversation_id = m.conversation_id
    where m.conversation_id = p_conversation_id and m.user_id = (select auth.uid())
      and (m.role in ('owner', 'admin') or not g.only_admins_edit_info)
  );
$$;

-- Account bootstrap ---------------------------------------------------------
create or replace function public.phone_hash(p_phone text)
returns text language sql immutable set search_path = '' as $$
  select case when coalesce(regexp_replace(p_phone, '\D', '', 'g'), '') = '' then null
         else encode(extensions.digest('+' || regexp_replace(p_phone, '\D', '', 'g'), 'sha256'), 'hex') end;
$$;

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, display_name, phone_hash)
  values (new.id,
          left(coalesce(nullif(trim(new.raw_user_meta_data ->> 'display_name'), ''), ''), 64),
          public.phone_hash(new.phone))
  on conflict (id) do nothing;
  insert into public.user_privacy_settings (user_id) values (new.id) on conflict do nothing;
  insert into public.user_notification_settings (user_id) values (new.id) on conflict do nothing;
  return new;
end $$;

create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_user();

create or replace function public.handle_user_phone_change()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  update public.profiles set phone_hash = public.phone_hash(new.phone) where id = new.id;
  return new;
end $$;

create trigger on_auth_user_phone_changed after update of phone on auth.users
for each row when (old.phone is distinct from new.phone)
execute function public.handle_user_phone_change();

-- Membership bookkeeping -------------------------------------------------------
create or replace function public.on_member_added()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.conversation_member_state (conversation_id, user_id, last_read_at)
  values (new.conversation_id, new.user_id, new.joined_at)
  on conflict do nothing;
  return null;
end $$;

create trigger conversation_members_added after insert on public.conversation_members
for each row execute function public.on_member_added();

-- When a group member leaves (or deletes their account) keep the group
-- administrable: promote someone if no owner/admin is left; drop empty groups.
create or replace function public.on_member_removed()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  v_type text;
  v_next uuid;
begin
  select c.type into v_type from public.conversations c where c.id = old.conversation_id;
  if v_type is null or v_type <> 'group' then
    return null;
  end if;
  if not exists (select 1 from public.conversation_members m where m.conversation_id = old.conversation_id) then
    delete from public.conversations where id = old.conversation_id;
    return null;
  end if;
  if old.role = 'owner' or not exists (
    select 1 from public.conversation_members m
    where m.conversation_id = old.conversation_id and m.role in ('owner', 'admin')
  ) then
    select m.user_id into v_next from public.conversation_members m
    where m.conversation_id = old.conversation_id
    order by (m.role = 'admin') desc, m.joined_at asc
    limit 1;
    update public.conversation_members
      set role = case when old.role = 'owner' then 'owner' else 'admin' end
      where conversation_id = old.conversation_id and user_id = v_next;
  end if;
  return null;
end $$;

create trigger conversation_members_removed after delete on public.conversation_members
for each row execute function public.on_member_removed();

-- Storage cleanup queue feeders --------------------------------------------------
create or replace function public.queue_storage_delete(p_bucket text, p_path text)
returns void language sql security definer set search_path = '' as $$
  insert into public.storage_cleanup_queue (bucket, path)
  select p_bucket, p_path where p_path is not null and p_path <> '';
$$;

create or replace function public.on_attachment_deleted()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  perform public.queue_storage_delete('media', old.path);
  return null;
end $$;
create trigger attachments_deleted after delete on public.attachments
for each row execute function public.on_attachment_deleted();

create or replace function public.on_status_deleted()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  perform public.queue_storage_delete('status', old.media_path);
  return null;
end $$;
create trigger statuses_deleted after delete on public.statuses
for each row execute function public.on_status_deleted();

create or replace function public.on_avatar_changed()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if tg_op = 'DELETE' then
    perform public.queue_storage_delete('avatars', old.avatar_path);
  elsif old.avatar_path is distinct from new.avatar_path then
    perform public.queue_storage_delete('avatars', old.avatar_path);
  end if;
  return null;
end $$;
create trigger profiles_avatar_changed after update of avatar_path or delete on public.profiles
for each row execute function public.on_avatar_changed();
create trigger groups_avatar_changed after update of avatar_path or delete on public.groups
for each row execute function public.on_avatar_changed();
create trigger communities_avatar_changed after update of avatar_path or delete on public.communities
for each row execute function public.on_avatar_changed();

-- Row level security policies ----------------------------------------------------
create policy profiles_select_own on public.profiles for select to authenticated
  using (id = (select auth.uid()));
create policy profiles_update_own on public.profiles for update to authenticated
  using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy privacy_select_own on public.user_privacy_settings for select to authenticated
  using (user_id = (select auth.uid()));
create policy privacy_update_own on public.user_privacy_settings for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

create policy audience_select_own on public.status_audience_list for select to authenticated
  using (user_id = (select auth.uid()));
create policy audience_insert_own on public.status_audience_list for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy audience_delete_own on public.status_audience_list for delete to authenticated
  using (user_id = (select auth.uid()));

create policy notif_settings_select_own on public.user_notification_settings for select to authenticated
  using (user_id = (select auth.uid()));
create policy notif_settings_update_own on public.user_notification_settings for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

create policy contacts_select_own on public.user_contacts for select to authenticated
  using (owner_id = (select auth.uid()));
create policy contacts_insert_own on public.user_contacts for insert to authenticated
  with check (owner_id = (select auth.uid()));
create policy contacts_delete_own on public.user_contacts for delete to authenticated
  using (owner_id = (select auth.uid()));

create policy blocks_select_own on public.user_blocks for select to authenticated
  using (blocker_id = (select auth.uid()));
create policy blocks_insert_own on public.user_blocks for insert to authenticated
  with check (blocker_id = (select auth.uid()));
create policy blocks_delete_own on public.user_blocks for delete to authenticated
  using (blocker_id = (select auth.uid()));

create policy devices_select_own on public.user_devices for select to authenticated
  using (user_id = (select auth.uid()));
create policy devices_insert_own on public.user_devices for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy devices_update_own on public.user_devices for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy devices_delete_own on public.user_devices for delete to authenticated
  using (user_id = (select auth.uid()));

create policy tokens_select_own on public.notification_tokens for select to authenticated
  using (user_id = (select auth.uid()));
create policy tokens_delete_own on public.notification_tokens for delete to authenticated
  using (user_id = (select auth.uid()));

create policy communities_select_member on public.communities for select to authenticated
  using (id in (select public.my_community_ids()));
create policy community_members_select_member on public.community_members for select to authenticated
  using (community_id in (select public.my_community_ids()));

create policy conversations_select_member on public.conversations for select to authenticated
  using (id in (select public.my_conversation_ids()));
create policy conversation_members_select_member on public.conversation_members for select to authenticated
  using (conversation_id in (select public.my_conversation_ids()));
create policy member_state_select_own on public.conversation_member_state for select to authenticated
  using (user_id = (select auth.uid()));
create policy member_state_update_own on public.conversation_member_state for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy groups_select_member on public.groups for select to authenticated
  using (conversation_id in (select public.my_conversation_ids()));

-- Members see messages sent after they joined. Messages silently withheld
-- from a recipient who blocked the sender stay visible only to the sender.
create policy messages_select_member on public.messages for select to authenticated
  using (
    exists (
      select 1 from public.conversation_members m
      where m.conversation_id = messages.conversation_id
        and m.user_id = (select auth.uid())
        and m.joined_at <= messages.created_at
    )
    and (not messages.hidden_for_recipients or messages.sender_id = (select auth.uid()))
  );

create policy attachments_select_member on public.attachments for select to authenticated
  using (conversation_id in (select public.my_conversation_ids()));

create policy reactions_select_member on public.message_reactions for select to authenticated
  using (conversation_id in (select public.my_conversation_ids()));
create policy reactions_insert_own on public.message_reactions for insert to authenticated
  with check (user_id = (select auth.uid()) and conversation_id in (select public.my_conversation_ids()));
create policy reactions_update_own on public.message_reactions for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()) and conversation_id in (select public.my_conversation_ids()));
create policy reactions_delete_own on public.message_reactions for delete to authenticated
  using (user_id = (select auth.uid()));

create policy stars_select_own on public.message_stars for select to authenticated
  using (user_id = (select auth.uid()));
create policy stars_insert_own on public.message_stars for insert to authenticated
  with check (user_id = (select auth.uid()) and conversation_id in (select public.my_conversation_ids()));
create policy stars_delete_own on public.message_stars for delete to authenticated
  using (user_id = (select auth.uid()));

create policy hidden_select_own on public.message_hidden for select to authenticated
  using (user_id = (select auth.uid()));
create policy hidden_insert_own on public.message_hidden for insert to authenticated
  with check (user_id = (select auth.uid()) and conversation_id in (select public.my_conversation_ids()));
create policy hidden_delete_own on public.message_hidden for delete to authenticated
  using (user_id = (select auth.uid()));

create policy pins_select_member on public.conversation_pins for select to authenticated
  using (conversation_id in (select public.my_conversation_ids()));

create policy statuses_select_visible on public.statuses for select to authenticated
  using (expires_at > now() and public.can_view_status(user_id));
create policy statuses_insert_own on public.statuses for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and (media_path is null or media_path like (select auth.uid())::text || '/%')
  );
create policy statuses_delete_own on public.statuses for delete to authenticated
  using (user_id = (select auth.uid()));

create policy status_views_select on public.status_views for select to authenticated
  using (
    viewer_id = (select auth.uid())
    or exists (select 1 from public.statuses s where s.id = status_views.status_id and s.user_id = (select auth.uid()))
  );
create policy status_views_insert_own on public.status_views for insert to authenticated
  with check (
    viewer_id = (select auth.uid())
    and exists (
      select 1 from public.statuses s
      where s.id = status_views.status_id and s.expires_at > now() and public.can_view_status(s.user_id)
    )
  );
create policy status_views_update_own on public.status_views for update to authenticated
  using (viewer_id = (select auth.uid())) with check (viewer_id = (select auth.uid()));

create policy status_mutes_select_own on public.status_mutes for select to authenticated
  using (user_id = (select auth.uid()));
create policy status_mutes_insert_own on public.status_mutes for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy status_mutes_delete_own on public.status_mutes for delete to authenticated
  using (user_id = (select auth.uid()));

create policy calls_select_participant on public.calls for select to authenticated
  using (id in (select public.my_call_ids()));
create policy call_participants_select on public.call_participants for select to authenticated
  using (call_id in (select public.my_call_ids()));

create policy reports_insert_own on public.reports for insert to authenticated
  with check (reporter_id = (select auth.uid()));

-- Table and column privileges (defence in depth on top of RLS) ----------------------
revoke all on all tables in schema public from anon;
revoke insert, update, delete on all tables in schema public from authenticated;
revoke all on public.storage_cleanup_queue, public.app_secrets from authenticated;

grant update (username, display_name, about, avatar_path, avatar_version, onboarded)
  on public.profiles to authenticated;
grant update (last_seen, online, profile_photo, about, status_audience, read_receipts, groups_add, calls_from, discoverable_by_phone)
  on public.user_privacy_settings to authenticated;
grant insert, delete on public.status_audience_list to authenticated;
grant update (messages, groups, calls, status, show_preview) on public.user_notification_settings to authenticated;
grant insert, delete on public.user_contacts to authenticated;
grant insert, delete on public.user_blocks to authenticated;
grant insert (user_id, identity_key, name, platform, app_version), delete on public.user_devices to authenticated;
grant update (name, app_version, last_active_at) on public.user_devices to authenticated;
grant delete on public.notification_tokens to authenticated;
grant update (muted_until, archived, pinned_at, cleared_at) on public.conversation_member_state to authenticated;
grant insert (message_id, conversation_id, user_id, emoji), update (emoji), delete on public.message_reactions to authenticated;
grant insert (user_id, message_id, conversation_id), delete on public.message_stars to authenticated;
grant insert (user_id, message_id, conversation_id), delete on public.message_hidden to authenticated;
grant insert (kind, body, background, font, media_path, caption, duration_ms), delete on public.statuses to authenticated;
grant insert (status_id, reaction), update (reaction) on public.status_views to authenticated;
grant insert (muted_user_id), delete on public.status_mutes to authenticated;
grant insert (reported_user_id, conversation_id, reason, details, evidence) on public.reports to authenticated;
