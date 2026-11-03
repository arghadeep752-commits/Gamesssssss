-- Group and community management RPCs.

create or replace function public.can_add_to_group(p_target uuid, p_actor uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.profiles p where p.id = p_target and p.onboarded)
     and not public.is_blocked_between(p_target, p_actor)
     and coalesce((
       select case s.groups_add when 'everyone' then true
                                when 'contacts' then public.is_contact(p_target, p_actor)
                                else false end
       from public.user_privacy_settings s where s.user_id = p_target
     ), false);
$$;

create or replace function public.add_members_internal(p_conversation_id uuid, p_actor uuid, p_user_ids uuid[])
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_added uuid[] := '{}';
  v_skipped uuid[] := '{}';
  v_uid uuid;
  v_count integer;
begin
  select count(*) into v_count from public.conversation_members m where m.conversation_id = p_conversation_id;
  foreach v_uid in array coalesce(p_user_ids, '{}'::uuid[]) loop
    if v_uid = p_actor or v_uid = any (v_added) then
      continue;
    end if;
    if exists (select 1 from public.conversation_members m where m.conversation_id = p_conversation_id and m.user_id = v_uid) then
      continue;
    end if;
    if v_count >= 256 or not public.can_add_to_group(v_uid, p_actor) then
      v_skipped := v_skipped || v_uid;
      continue;
    end if;
    insert into public.conversation_members (conversation_id, user_id, role, added_by)
    values (p_conversation_id, v_uid, 'member', p_actor) on conflict do nothing;
    v_added := v_added || v_uid;
    v_count := v_count + 1;
  end loop;
  if coalesce(array_length(v_added, 1), 0) > 0 then
    perform public.post_system_message(p_conversation_id,
      jsonb_build_object('type', 'members_added', 'actor', p_actor, 'targets', to_jsonb(v_added)));
  end if;
  return jsonb_build_object('added', to_jsonb(v_added), 'skipped', to_jsonb(v_skipped));
end $$;

create or replace function public.create_group(p_name text, p_description text default '', p_member_ids uuid[] default '{}', p_community_id uuid default null)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_id uuid;
  v_name text := left(trim(coalesce(p_name, '')), 64);
  v_result jsonb;
begin
  if char_length(v_name) = 0 then
    raise exception 'name_required' using errcode = '22023';
  end if;
  if coalesce(array_length(p_member_ids, 1), 0) > 255 then
    raise exception 'too_many_members' using errcode = '22023';
  end if;
  if p_community_id is not null and coalesce(public.community_role(p_community_id), '') not in ('owner', 'admin') then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  insert into public.conversations (type, created_by, community_id) values ('group', v_me, p_community_id) returning id into v_id;
  insert into public.groups (conversation_id, name, description, invite_code)
  values (v_id, v_name, left(coalesce(p_description, ''), 512), public.new_invite_code());
  insert into public.conversation_members (conversation_id, user_id, role, added_by) values (v_id, v_me, 'owner', v_me);
  perform public.post_system_message(v_id, jsonb_build_object('type', 'group_created', 'actor', v_me, 'name', v_name));
  v_result := public.add_members_internal(v_id, v_me, p_member_ids);
  return v_result || jsonb_build_object('conversation_id', v_id);
end $$;

create or replace function public.add_group_members(p_conversation_id uuid, p_user_ids uuid[])
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_role text := public.member_role(p_conversation_id);
  v_group record;
begin
  select g.* into v_group from public.groups g where g.conversation_id = p_conversation_id;
  if v_role is null or v_group.conversation_id is null then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  if (v_group.only_admins_add or v_group.is_announcement) and v_role not in ('owner', 'admin') then
    raise exception 'only_admins_can_add' using errcode = '42501';
  end if;
  return public.add_members_internal(p_conversation_id, v_me, p_user_ids);
end $$;

create or replace function public.update_group_info(p_conversation_id uuid, p_name text default null, p_description text default null, p_avatar_path text default null, p_remove_avatar boolean default false)
returns void language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_old record;
  v_name text := left(trim(coalesce(p_name, '')), 64);
begin
  if not public.can_edit_group_info(p_conversation_id) then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  if p_avatar_path is not null and p_avatar_path not like 'groups/' || p_conversation_id::text || '/%' then
    raise exception 'invalid_avatar_path' using errcode = '22023';
  end if;
  select g.* into v_old from public.groups g where g.conversation_id = p_conversation_id;
  update public.groups g set
    name = case when char_length(v_name) > 0 then v_name else g.name end,
    description = case when p_description is not null then left(p_description, 512) else g.description end,
    avatar_path = case when p_remove_avatar then null when p_avatar_path is not null then p_avatar_path else g.avatar_path end,
    avatar_version = case when p_remove_avatar or p_avatar_path is not null then g.avatar_version + 1 else g.avatar_version end
  where g.conversation_id = p_conversation_id;
  if char_length(v_name) > 0 and v_name <> v_old.name then
    perform public.post_system_message(p_conversation_id, jsonb_build_object('type', 'group_renamed', 'actor', v_me, 'name', v_name));
  end if;
  if p_description is not null and left(p_description, 512) is distinct from v_old.description then
    perform public.post_system_message(p_conversation_id, jsonb_build_object('type', 'description_changed', 'actor', v_me));
  end if;
  if p_remove_avatar or p_avatar_path is not null then
    perform public.post_system_message(p_conversation_id, jsonb_build_object('type', 'photo_changed', 'actor', v_me));
  end if;
end $$;

create or replace function public.update_group_settings(p_conversation_id uuid, p_only_admins_send boolean default null, p_only_admins_edit_info boolean default null, p_only_admins_add boolean default null)
returns void language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_old record;
begin
  if coalesce(public.member_role(p_conversation_id), '') not in ('owner', 'admin') then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  select g.* into v_old from public.groups g where g.conversation_id = p_conversation_id;
  if v_old.conversation_id is null then
    raise exception 'not_a_group' using errcode = '22023';
  end if;
  update public.groups g set
    only_admins_send = coalesce(p_only_admins_send, g.only_admins_send),
    only_admins_edit_info = coalesce(p_only_admins_edit_info, g.only_admins_edit_info),
    only_admins_add = coalesce(p_only_admins_add, g.only_admins_add)
  where g.conversation_id = p_conversation_id;
  if p_only_admins_send is not null and p_only_admins_send <> v_old.only_admins_send then
    perform public.post_system_message(p_conversation_id,
      jsonb_build_object('type', 'send_permission_changed', 'actor', v_me, 'only_admins', p_only_admins_send));
  end if;
end $$;

create or replace function public.set_member_role(p_conversation_id uuid, p_user_id uuid, p_admin boolean)
returns void language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_target_role text;
begin
  if coalesce(public.member_role(p_conversation_id), '') not in ('owner', 'admin') then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  select m.role into v_target_role from public.conversation_members m
  where m.conversation_id = p_conversation_id and m.user_id = p_user_id;
  if v_target_role is null then
    raise exception 'not_a_member' using errcode = 'P0002';
  end if;
  if v_target_role = 'owner' then
    raise exception 'cannot_change_owner' using errcode = '42501';
  end if;
  if (p_admin and v_target_role = 'admin') or (not p_admin and v_target_role = 'member') then
    return;
  end if;
  update public.conversation_members m set role = case when p_admin then 'admin' else 'member' end
  where m.conversation_id = p_conversation_id and m.user_id = p_user_id;
  perform public.post_system_message(p_conversation_id,
    jsonb_build_object('type', case when p_admin then 'admin_added' else 'admin_removed' end, 'actor', v_me, 'targets', jsonb_build_array(p_user_id)));
end $$;

create or replace function public.get_group_invite(p_conversation_id uuid, p_reset boolean default false)
returns text language plpgsql security definer set search_path = '' as $$
declare v_code text;
begin
  perform public.require_user();
  if coalesce(public.member_role(p_conversation_id), '') not in ('owner', 'admin') then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  if p_reset then
    update public.groups g set invite_code = public.new_invite_code() where g.conversation_id = p_conversation_id;
  end if;
  select g.invite_code into v_code from public.groups g where g.conversation_id = p_conversation_id;
  if v_code is null then
    update public.groups g set invite_code = public.new_invite_code() where g.conversation_id = p_conversation_id
    returning g.invite_code into v_code;
  end if;
  return v_code;
end $$;

create or replace function public.preview_group_invite(p_code text)
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'conversation_id', g.conversation_id, 'name', g.name, 'description', g.description,
    'member_count', (select count(*) from public.conversation_members m where m.conversation_id = g.conversation_id),
    'is_member', exists (select 1 from public.conversation_members m where m.conversation_id = g.conversation_id and m.user_id = (select auth.uid())),
    'is_announcement', g.is_announcement)
  from public.groups g
  where (select auth.uid()) is not null and g.invite_code = p_code and not g.is_announcement;
$$;

create or replace function public.join_group_by_invite(p_code text)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_conv uuid;
  v_announcement boolean;
begin
  select g.conversation_id, g.is_announcement into v_conv, v_announcement from public.groups g where g.invite_code = p_code;
  if v_conv is null or v_announcement then
    raise exception 'invite_invalid' using errcode = 'P0002';
  end if;
  if exists (select 1 from public.conversation_members m where m.conversation_id = v_conv and m.user_id = v_me) then
    return v_conv;
  end if;
  if (select count(*) from public.conversation_members m where m.conversation_id = v_conv) >= 256 then
    raise exception 'group_full' using errcode = '54000';
  end if;
  insert into public.conversation_members (conversation_id, user_id, role) values (v_conv, v_me, 'member');
  perform public.post_system_message(v_conv, jsonb_build_object('type', 'member_joined_link', 'actor', v_me));
  return v_conv;
end $$;

create or replace function public.get_group_members(p_conversation_id uuid)
returns table (user_id uuid, role text, joined_at timestamptz, display_name text, username text, avatar_path text, avatar_version integer)
language sql stable security definer set search_path = '' as $$
  select m.user_id, m.role, m.joined_at, p.display_name, p.username,
         case when public.can_see_field(p.id, s.profile_photo) then p.avatar_path end, p.avatar_version
  from public.conversation_members m
  join public.profiles p on p.id = m.user_id
  left join public.user_privacy_settings s on s.user_id = p.id
  where m.conversation_id = p_conversation_id and public.is_member(p_conversation_id)
  order by case m.role when 'owner' then 0 when 'admin' then 1 else 2 end, p.display_name;
$$;

-- Communities ------------------------------------------------------------------
create or replace function public.create_community(p_name text, p_description text default '')
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_name text := left(trim(coalesce(p_name, '')), 64);
  v_id uuid;
  v_conv uuid;
begin
  if char_length(v_name) = 0 then
    raise exception 'name_required' using errcode = '22023';
  end if;
  insert into public.communities (name, description, invite_code, created_by)
  values (v_name, left(coalesce(p_description, ''), 512), public.new_invite_code(), v_me)
  returning id into v_id;
  insert into public.community_members (community_id, user_id, role) values (v_id, v_me, 'owner');
  insert into public.conversations (type, created_by, community_id) values ('group', v_me, v_id) returning id into v_conv;
  insert into public.groups (conversation_id, name, description, is_announcement, only_admins_send, only_admins_edit_info, only_admins_add)
  values (v_conv, v_name, 'Announcements', true, true, true, true);
  insert into public.conversation_members (conversation_id, user_id, role, added_by) values (v_conv, v_me, 'owner', v_me);
  perform public.post_system_message(v_conv, jsonb_build_object('type', 'community_created', 'actor', v_me, 'name', v_name));
  update public.communities c set announcement_conversation_id = v_conv where c.id = v_id;
  return jsonb_build_object('community_id', v_id, 'announcement_conversation_id', v_conv);
end $$;

create or replace function public.get_my_communities()
returns table (id uuid, name text, description text, avatar_path text, avatar_version integer, role text,
               member_count integer, group_count integer, announcement_conversation_id uuid)
language sql stable security definer set search_path = '' as $$
  select c.id, c.name, c.description, c.avatar_path, c.avatar_version, cm.role,
         (select count(*)::int from public.community_members x where x.community_id = c.id),
         (select count(*)::int from public.conversations v where v.community_id = c.id),
         c.announcement_conversation_id
  from public.community_members cm
  join public.communities c on c.id = cm.community_id
  where cm.user_id = (select auth.uid())
  order by c.name;
$$;

create or replace function public.get_community(p_community_id uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'id', c.id, 'name', c.name, 'description', c.description, 'avatar_path', c.avatar_path,
    'avatar_version', c.avatar_version, 'role', public.community_role(c.id),
    'announcement_conversation_id', c.announcement_conversation_id,
    'member_count', (select count(*) from public.community_members x where x.community_id = c.id),
    'groups', coalesce((
      select jsonb_agg(jsonb_build_object(
        'conversation_id', g.conversation_id, 'name', g.name, 'description', g.description,
        'avatar_path', g.avatar_path, 'avatar_version', g.avatar_version, 'is_announcement', g.is_announcement,
        'member_count', (select count(*) from public.conversation_members m where m.conversation_id = g.conversation_id),
        'is_member', exists (select 1 from public.conversation_members m where m.conversation_id = g.conversation_id and m.user_id = (select auth.uid())))
        order by g.is_announcement desc, g.name)
      from public.conversations v join public.groups g on g.conversation_id = v.id
      where v.community_id = c.id), '[]'::jsonb))
  from public.communities c
  where c.id = p_community_id and public.community_role(c.id) is not null;
$$;

create or replace function public.create_community_group(p_community_id uuid, p_name text, p_description text default '')
returns jsonb language plpgsql security definer set search_path = '' as $$
begin
  return public.create_group(p_name, p_description, '{}'::uuid[], p_community_id);
end $$;

create or replace function public.join_community_group(p_conversation_id uuid)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_community uuid;
begin
  select v.community_id into v_community from public.conversations v where v.id = p_conversation_id;
  if v_community is null or public.community_role(v_community) is null then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  if not exists (select 1 from public.conversation_members m where m.conversation_id = p_conversation_id and m.user_id = v_me) then
    insert into public.conversation_members (conversation_id, user_id, role) values (p_conversation_id, v_me, 'member');
    perform public.post_system_message(p_conversation_id, jsonb_build_object('type', 'member_joined_community', 'actor', v_me));
  end if;
  return p_conversation_id;
end $$;

create or replace function public.get_community_invite(p_community_id uuid, p_reset boolean default false)
returns text language plpgsql security definer set search_path = '' as $$
declare v_code text;
begin
  perform public.require_user();
  if coalesce(public.community_role(p_community_id), '') not in ('owner', 'admin') then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  if p_reset then
    update public.communities c set invite_code = public.new_invite_code() where c.id = p_community_id;
  end if;
  select c.invite_code into v_code from public.communities c where c.id = p_community_id;
  return v_code;
end $$;

create or replace function public.preview_community_invite(p_code text)
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object('community_id', c.id, 'name', c.name, 'description', c.description,
    'member_count', (select count(*) from public.community_members x where x.community_id = c.id),
    'is_member', public.community_role(c.id) is not null)
  from public.communities c
  where (select auth.uid()) is not null and c.invite_code = p_code;
$$;

create or replace function public.join_community_by_invite(p_code text)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  v_me uuid := public.require_user();
  v_id uuid;
  v_conv uuid;
begin
  select c.id, c.announcement_conversation_id into v_id, v_conv from public.communities c where c.invite_code = p_code;
  if v_id is null then
    raise exception 'invite_invalid' using errcode = 'P0002';
  end if;
  insert into public.community_members (community_id, user_id, role) values (v_id, v_me, 'member') on conflict do nothing;
  if v_conv is not null then
    insert into public.conversation_members (conversation_id, user_id, role) values (v_conv, v_me, 'member') on conflict do nothing;
  end if;
  return v_id;
end $$;

create or replace function public.update_community(p_community_id uuid, p_name text default null, p_description text default null, p_avatar_path text default null, p_remove_avatar boolean default false)
returns void language plpgsql security definer set search_path = '' as $$
declare v_name text := left(trim(coalesce(p_name, '')), 64);
begin
  perform public.require_user();
  if coalesce(public.community_role(p_community_id), '') not in ('owner', 'admin') then
    raise exception 'not_allowed' using errcode = '42501';
  end if;
  if p_avatar_path is not null and p_avatar_path not like 'communities/' || p_community_id::text || '/%' then
    raise exception 'invalid_avatar_path' using errcode = '22023';
  end if;
  update public.communities c set
    name = case when char_length(v_name) > 0 then v_name else c.name end,
    description = case when p_description is not null then left(p_description, 512) else c.description end,
    avatar_path = case when p_remove_avatar then null when p_avatar_path is not null then p_avatar_path else c.avatar_path end,
    avatar_version = case when p_remove_avatar or p_avatar_path is not null then c.avatar_version + 1 else c.avatar_version end
  where c.id = p_community_id;
end $$;
