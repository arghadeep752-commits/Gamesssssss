-- Function privileges: nothing is callable by anonymous clients; signed-in
-- users can call the public RPCs and the helpers used inside RLS policies.
do $$
declare r record;
begin
  for r in
    select p.oid::regprocedure as sig from pg_proc p
    where p.pronamespace = 'public'::regnamespace and p.prokind = 'f'
  loop
    execute format('revoke all on function %s from public, anon, authenticated', r.sig);
    execute format('grant execute on function %s to service_role', r.sig);
  end loop;
end $$;

do $$
declare
  r record;
  allowed text[] := array[
    -- RPCs
    'is_username_available', 'get_profiles', 'search_users', 'match_contacts', 'register_device',
    'register_push_token', 'heartbeat', 'get_presence', 'get_conversation_devices', 'get_or_create_direct',
    'get_chat_list', 'get_messages', 'sync_messages', 'mark_delivered', 'mark_all_delivered', 'mark_read',
    'send_message', 'edit_message', 'delete_message_for_everyone', 'create_group', 'add_group_members',
    'update_group_info', 'update_group_settings', 'set_member_role', 'get_group_invite', 'preview_group_invite',
    'join_group_by_invite', 'get_group_members', 'create_community', 'get_my_communities', 'get_community',
    'create_community_group', 'join_community_group', 'get_community_invite', 'preview_community_invite',
    'join_community_by_invite', 'update_community', 'start_call', 'answer_call', 'end_call', 'get_call',
    'get_incoming_call', 'get_call_history', 'get_status_feed', 'get_status_viewers', 'mark_status_viewed',
    'export_my_data',
    -- helpers referenced by RLS / realtime / storage policies
    'try_uuid', 'my_conversation_ids', 'my_call_ids', 'my_community_ids', 'can_view_status', 'can_view_avatar',
    'can_view_presence', 'can_edit_group_info', 'can_edit_group_info_text', 'is_community_member_text',
    'is_community_admin_text', 'can_pin', 'can_remove_member', 'member_role', 'community_role'
  ];
begin
  for r in
    select p.oid::regprocedure as sig from pg_proc p
    where p.pronamespace = 'public'::regnamespace and p.prokind = 'f' and p.proname = any (allowed)
  loop
    execute format('grant execute on function %s to authenticated', r.sig);
  end loop;
end $$;

alter default privileges in schema public revoke execute on functions from public, anon;

-- Scheduled jobs ---------------------------------------------------------------
create extension if not exists pg_cron;
create extension if not exists pg_net with schema extensions;

insert into public.app_secrets (key, value)
values ('cron_key', encode(extensions.gen_random_bytes(32), 'hex'))
on conflict (key) do nothing;

select cron.schedule('hime-expire-calls', '*/5 * * * *', $job$ select public.expire_stale_calls(); $job$);

select cron.schedule('hime-cleanup', '23 * * * *', $job$
  select net.http_post(
    url := 'https://xsoueofjwwfqhsawnoux.supabase.co/functions/v1/cleanup',
    headers := jsonb_build_object('Content-Type', 'application/json',
                                  'x-hime-cron', (select s.value from public.app_secrets s where s.key = 'cron_key')),
    body := '{}'::jsonb,
    timeout_milliseconds := 30000
  );
$job$);
