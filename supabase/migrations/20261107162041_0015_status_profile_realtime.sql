-- Live status and profile updates on the private user:<id> topics.

-- Everyone who may see p_owner's status updates (mirrors can_view_status).
create or replace function public.status_audience_ids(p_owner uuid)
returns setof uuid
language sql
stable
security definer
set search_path = ''
as $$
  with s as (
    select status_audience from public.user_privacy_settings where user_id = p_owner
  ),
  contacts as (
    select c.contact_id as id from public.user_contacts c where c.owner_id = p_owner
    union
    select m2.user_id
    from public.conversation_members m
    join public.conversations c on c.id = m.conversation_id and c.direct_key is not null
    join public.conversation_members m2 on m2.conversation_id = c.id and m2.user_id <> p_owner
    where m.user_id = p_owner and m.engaged
  ),
  cand as (
    select id from contacts where (select status_audience from s) in ('contacts', 'contacts_except')
    union
    select l.member_id from public.status_audience_list l
    where l.user_id = p_owner and l.list_kind = 'only' and (select status_audience from s) = 'only_share_with'
  )
  select distinct cand.id from cand
  where cand.id is not null
    and cand.id <> p_owner
    and not public.is_blocked_between(p_owner, cand.id)
    and not (
      (select status_audience from s) = 'contacts_except'
      and exists (select 1 from public.status_audience_list l
                  where l.user_id = p_owner and l.list_kind = 'except' and l.member_id = cand.id)
    );
$$;
revoke all on function public.status_audience_ids(uuid) from public, anon, authenticated;

create or replace function public.rt_on_status()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v record;
  r record;
  v_payload jsonb;
begin
  if tg_op = 'DELETE' then v := old; else v := new; end if;
  v_payload := jsonb_build_object('user_id', v.user_id, 'status_id', v.id, 'op', lower(tg_op));
  perform public.rt_send(v.user_id, 'status', v_payload);
  for r in select a.id from public.status_audience_ids(v.user_id) as a(id) loop
    perform public.rt_send(r.id, 'status', v_payload);
  end loop;
  return null;
end $$;

drop trigger if exists statuses_realtime on public.statuses;
create trigger statuses_realtime
  after insert or delete on public.statuses
  for each row execute function public.rt_on_status();

-- Tell the owner when someone views (or reacts to) one of their statuses.
create or replace function public.rt_on_status_view()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare v_owner uuid;
begin
  select s.user_id into v_owner from public.statuses s where s.id = new.status_id;
  if v_owner is not null then
    perform public.rt_send(v_owner, 'status_view', jsonb_build_object('status_id', new.status_id));
  end if;
  return null;
end $$;

drop trigger if exists status_views_realtime on public.status_views;
create trigger status_views_realtime
  after insert or update on public.status_views
  for each row execute function public.rt_on_status_view();

-- Profile changes (name, about, photo, username) reach people who chat with the
-- user or have them in their contacts; clients re-fetch the privacy-masked profile.
create or replace function public.rt_on_profile_change()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  r record;
  v_payload jsonb;
begin
  if new.display_name is not distinct from old.display_name
     and new.about is not distinct from old.about
     and new.username is not distinct from old.username
     and new.avatar_path is not distinct from old.avatar_path
     and new.avatar_version is not distinct from old.avatar_version then
    return null;
  end if;
  v_payload := jsonb_build_object('user_id', new.id);
  perform public.rt_send(new.id, 'profile', v_payload);
  for r in
    select m2.user_id as id
    from public.conversation_members m
    join public.conversation_members m2 on m2.conversation_id = m.conversation_id and m2.user_id <> new.id
    where m.user_id = new.id
    union
    select c.owner_id from public.user_contacts c where c.contact_id = new.id
  loop
    perform public.rt_send(r.id, 'profile', v_payload);
  end loop;
  return null;
end $$;

drop trigger if exists profiles_realtime on public.profiles;
create trigger profiles_realtime
  after update on public.profiles
  for each row execute function public.rt_on_profile_change();

revoke all on function public.rt_on_status() from public, anon, authenticated;
revoke all on function public.rt_on_status_view() from public, anon, authenticated;
revoke all on function public.rt_on_profile_change() from public, anon, authenticated;
