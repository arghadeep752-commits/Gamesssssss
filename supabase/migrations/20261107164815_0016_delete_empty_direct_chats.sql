-- When the last member of any chat is gone (e.g. both people in a direct chat
-- deleted their accounts), delete the chat so its encrypted messages and
-- attachments are removed too. Groups keep their owner hand-over logic.
create or replace function public.on_member_removed()
returns trigger
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_type text;
  v_next uuid;
begin
  select c.type into v_type from public.conversations c where c.id = old.conversation_id;
  if v_type is null then
    return null;
  end if;
  if not exists (select 1 from public.conversation_members m where m.conversation_id = old.conversation_id) then
    delete from public.conversations where id = old.conversation_id;
    return null;
  end if;
  if v_type <> 'group' then
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
end $function$;

-- Remove chats that already lost all their members.
delete from public.conversations c
where not exists (select 1 from public.conversation_members m where m.conversation_id = c.id);
