-- Attachments soft-deleted earlier were already queued for blob removal.
create or replace function public.on_attachment_deleted()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if old.deleted_at is null then
    perform public.queue_storage_delete('media', old.path);
  end if;
  return null;
end $$;
revoke all on function public.on_attachment_deleted() from public, anon, authenticated;
