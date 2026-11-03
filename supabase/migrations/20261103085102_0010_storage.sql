-- Private buckets. Chat media is encrypted on the device before upload, so
-- the media bucket only accepts opaque binary blobs.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types) values
  ('avatars', 'avatars', false, 5242880, array['image/jpeg', 'image/png', 'image/webp']),
  ('media', 'media', false, 52428800, array['application/octet-stream']),
  ('status', 'status', false, 31457280, array['image/jpeg', 'image/png', 'image/webp', 'video/mp4', 'video/3gpp', 'video/quicktime', 'video/webm'])
on conflict (id) do nothing;

create or replace function public.is_community_member_text(p_community text)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.community_members m
                 where m.community_id = public.try_uuid(p_community) and m.user_id = (select auth.uid()));
$$;

create or replace function public.is_community_admin_text(p_community text)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.community_members m
                 where m.community_id = public.try_uuid(p_community) and m.user_id = (select auth.uid())
                   and m.role in ('owner', 'admin'));
$$;

create or replace function public.can_edit_group_info_text(p_conversation text)
returns boolean language sql stable security definer set search_path = '' as $$
  select public.can_edit_group_info(public.try_uuid(p_conversation));
$$;

-- Avatars: users/<uid>/..., groups/<conversation id>/..., communities/<id>/...
create policy avatars_read on storage.objects for select to authenticated using (
  bucket_id = 'avatars' and (
    ((storage.foldername(name))[1] = 'users' and public.can_view_avatar((storage.foldername(name))[2]))
    or ((storage.foldername(name))[1] = 'groups'
        and public.try_uuid((storage.foldername(name))[2]) in (select public.my_conversation_ids()))
    or ((storage.foldername(name))[1] = 'communities' and public.is_community_member_text((storage.foldername(name))[2]))
  )
);
create policy avatars_insert on storage.objects for insert to authenticated with check (
  bucket_id = 'avatars' and (
    ((storage.foldername(name))[1] = 'users' and (storage.foldername(name))[2] = (select auth.uid())::text)
    or ((storage.foldername(name))[1] = 'groups' and public.can_edit_group_info_text((storage.foldername(name))[2]))
    or ((storage.foldername(name))[1] = 'communities' and public.is_community_admin_text((storage.foldername(name))[2]))
  )
);
create policy avatars_delete on storage.objects for delete to authenticated using (
  bucket_id = 'avatars' and owner_id = (select auth.uid())::text
);

-- Media: <conversation id>/<random id>; members only.
create policy media_read on storage.objects for select to authenticated using (
  bucket_id = 'media'
  and public.try_uuid((storage.foldername(name))[1]) in (select public.my_conversation_ids())
);
create policy media_insert on storage.objects for insert to authenticated with check (
  bucket_id = 'media'
  and public.try_uuid((storage.foldername(name))[1]) in (select public.my_conversation_ids())
);
create policy media_delete on storage.objects for delete to authenticated using (
  bucket_id = 'media' and owner_id = (select auth.uid())::text
);

-- Status media: <uid>/<random id>; readable while the status is live and
-- the viewer is in its audience.
create policy status_read on storage.objects for select to authenticated using (
  bucket_id = 'status' and (
    (storage.foldername(name))[1] = (select auth.uid())::text
    or exists (
      select 1 from public.statuses s
      where s.media_path = storage.objects.name and s.expires_at > now() and public.can_view_status(s.user_id)
    )
  )
);
create policy status_insert on storage.objects for insert to authenticated with check (
  bucket_id = 'status' and (storage.foldername(name))[1] = (select auth.uid())::text
);
create policy status_delete on storage.objects for delete to authenticated using (
  bucket_id = 'status' and (storage.foldername(name))[1] = (select auth.uid())::text
);
