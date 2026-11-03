-- Hime core schema: identity, privacy, contacts, devices, conversations,
-- messages (end-to-end encrypted envelopes), media, statuses, calls.
create extension if not exists pg_trgm with schema extensions;

create or replace function public.set_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at := now();
  return new;
end $$;

-- Profiles ---------------------------------------------------------------
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  username text unique,
  display_name text not null default '' check (char_length(display_name) <= 64),
  about text not null default 'Hey there! I''m on Hime.' check (char_length(about) <= 140),
  avatar_path text check (avatar_path is null or char_length(avatar_path) <= 256),
  avatar_version integer not null default 0,
  phone_hash text,
  onboarded boolean not null default false,
  last_seen_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint profiles_username_format check (username is null or username ~ '^[a-z0-9_.]{3,24}$')
);
create index profiles_phone_hash_idx on public.profiles (phone_hash) where phone_hash is not null;
create index profiles_username_trgm_idx on public.profiles using gin (username extensions.gin_trgm_ops);
create index profiles_display_name_trgm_idx on public.profiles using gin (lower(display_name) extensions.gin_trgm_ops);
create trigger profiles_updated_at before update on public.profiles for each row execute function public.set_updated_at();

create table public.user_privacy_settings (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  last_seen text not null default 'everyone' check (last_seen in ('everyone', 'contacts', 'nobody')),
  online text not null default 'everyone' check (online in ('everyone', 'same_as_last_seen')),
  profile_photo text not null default 'everyone' check (profile_photo in ('everyone', 'contacts', 'nobody')),
  about text not null default 'everyone' check (about in ('everyone', 'contacts', 'nobody')),
  status_audience text not null default 'contacts' check (status_audience in ('contacts', 'contacts_except', 'only_share_with')),
  read_receipts boolean not null default true,
  groups_add text not null default 'everyone' check (groups_add in ('everyone', 'contacts', 'nobody')),
  calls_from text not null default 'everyone' check (calls_from in ('everyone', 'contacts')),
  discoverable_by_phone boolean not null default true,
  updated_at timestamptz not null default now()
);
create trigger user_privacy_settings_updated_at before update on public.user_privacy_settings for each row execute function public.set_updated_at();

create table public.status_audience_list (
  user_id uuid not null references public.profiles (id) on delete cascade,
  list_kind text not null check (list_kind in ('except', 'only')),
  member_id uuid not null references public.profiles (id) on delete cascade,
  primary key (user_id, list_kind, member_id),
  check (user_id <> member_id)
);

create table public.user_notification_settings (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  messages boolean not null default true,
  groups boolean not null default true,
  calls boolean not null default true,
  status boolean not null default false,
  show_preview boolean not null default true,
  updated_at timestamptz not null default now()
);
create trigger user_notification_settings_updated_at before update on public.user_notification_settings for each row execute function public.set_updated_at();

create table public.user_contacts (
  owner_id uuid not null references public.profiles (id) on delete cascade,
  contact_id uuid not null references public.profiles (id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (owner_id, contact_id),
  check (owner_id <> contact_id)
);
create index user_contacts_contact_idx on public.user_contacts (contact_id);

create table public.user_blocks (
  blocker_id uuid not null references public.profiles (id) on delete cascade,
  blocked_id uuid not null references public.profiles (id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (blocker_id, blocked_id),
  check (blocker_id <> blocked_id)
);
create index user_blocks_blocked_idx on public.user_blocks (blocked_id);

-- Each app installation is a device with its own X25519 identity key.
create table public.user_devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  identity_key text not null check (identity_key ~ '^[A-Za-z0-9+/]{43}=$'),
  name text not null default 'Android phone' check (char_length(name) <= 64),
  platform text not null default 'android' check (platform in ('android', 'ios', 'web', 'other')),
  app_version text check (char_length(app_version) <= 32),
  created_at timestamptz not null default now(),
  last_active_at timestamptz not null default now(),
  unique (user_id, identity_key)
);
create index user_devices_user_idx on public.user_devices (user_id);

create table public.notification_tokens (
  token text primary key check (char_length(token) <= 4096),
  user_id uuid not null references public.profiles (id) on delete cascade,
  device_id uuid references public.user_devices (id) on delete cascade,
  platform text not null default 'android' check (platform in ('android', 'ios', 'web')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index notification_tokens_user_idx on public.notification_tokens (user_id);
create index notification_tokens_device_idx on public.notification_tokens (device_id);

-- Communities, conversations and groups -----------------------------------
create table public.communities (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 1 and 64),
  description text not null default '' check (char_length(description) <= 512),
  avatar_path text check (avatar_path is null or char_length(avatar_path) <= 256),
  avatar_version integer not null default 0,
  invite_code text unique,
  announcement_conversation_id uuid,
  created_by uuid references public.profiles (id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger communities_updated_at before update on public.communities for each row execute function public.set_updated_at();

create table public.community_members (
  community_id uuid not null references public.communities (id) on delete cascade,
  user_id uuid not null references public.profiles (id) on delete cascade,
  role text not null default 'member' check (role in ('owner', 'admin', 'member')),
  joined_at timestamptz not null default now(),
  primary key (community_id, user_id)
);
create index community_members_user_idx on public.community_members (user_id);

create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  type text not null check (type in ('direct', 'group')),
  direct_key text unique,
  community_id uuid references public.communities (id) on delete set null,
  created_by uuid references public.profiles (id) on delete set null,
  created_at timestamptz not null default now(),
  last_message_at timestamptz,
  last_message_id uuid,
  constraint conversations_direct_key check ((type = 'direct') = (direct_key is not null))
);
create index conversations_community_idx on public.conversations (community_id) where community_id is not null;
create index conversations_created_by_idx on public.conversations (created_by);
alter table public.communities
  add constraint communities_announcement_fk foreign key (announcement_conversation_id)
  references public.conversations (id) on delete set null;
create index communities_announcement_idx on public.communities (announcement_conversation_id);
create index communities_created_by_idx on public.communities (created_by);

create table public.conversation_members (
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  user_id uuid not null references public.profiles (id) on delete cascade,
  role text not null default 'member' check (role in ('owner', 'admin', 'member')),
  added_by uuid references public.profiles (id) on delete set null,
  joined_at timestamptz not null default now(),
  delivered_up_to timestamptz,
  read_up_to timestamptz,
  primary key (conversation_id, user_id)
);
create index conversation_members_user_idx on public.conversation_members (user_id);
create index conversation_members_added_by_idx on public.conversation_members (added_by);

-- Private, per-member chat state (never visible to other members).
create table public.conversation_member_state (
  conversation_id uuid not null,
  user_id uuid not null,
  last_read_at timestamptz,
  muted_until timestamptz,
  archived boolean not null default false,
  pinned_at timestamptz,
  cleared_at timestamptz,
  primary key (conversation_id, user_id),
  foreign key (conversation_id, user_id) references public.conversation_members (conversation_id, user_id) on delete cascade
);
create index conversation_member_state_user_idx on public.conversation_member_state (user_id);

create table public.groups (
  conversation_id uuid primary key references public.conversations (id) on delete cascade,
  name text not null check (char_length(name) between 1 and 64),
  description text not null default '' check (char_length(description) <= 512),
  avatar_path text check (avatar_path is null or char_length(avatar_path) <= 256),
  avatar_version integer not null default 0,
  invite_code text unique,
  only_admins_send boolean not null default false,
  only_admins_edit_info boolean not null default true,
  only_admins_add boolean not null default false,
  is_announcement boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger groups_updated_at before update on public.groups for each row execute function public.set_updated_at();

-- Messages: the server only stores ciphertext envelopes. `keys` maps each
-- recipient device id to the message key wrapped for that device.
create table public.messages (
  id uuid primary key,
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  sender_id uuid references public.profiles (id) on delete set null,
  sender_device_id uuid,
  kind text not null check (kind in ('text', 'image', 'video', 'voice', 'audio', 'document', 'contact', 'location', 'system', 'call')),
  ciphertext text check (char_length(ciphertext) <= 98304),
  nonce text check (char_length(nonce) <= 64),
  eph_key text check (char_length(eph_key) <= 64),
  keys jsonb,
  system jsonb,
  hidden_for_recipients boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  edited_at timestamptz,
  deleted_at timestamptz,
  constraint messages_id_conversation unique (id, conversation_id),
  constraint messages_payload_present check (
    deleted_at is not null
    or (kind in ('system', 'call') and system is not null)
    or (ciphertext is not null and nonce is not null and eph_key is not null and keys is not null)
  ),
  constraint messages_keys_size check (keys is null or pg_column_size(keys) <= 262144),
  constraint messages_system_size check (system is null or pg_column_size(system) <= 8192)
);
create index messages_conversation_created_idx on public.messages (conversation_id, created_at desc);
create index messages_conversation_updated_idx on public.messages (conversation_id, updated_at);
create index messages_sender_created_idx on public.messages (sender_id, created_at desc);
alter table public.conversations
  add constraint conversations_last_message_fk foreign key (last_message_id)
  references public.messages (id) on delete set null;
create index conversations_last_message_idx on public.conversations (last_message_id);

create table public.attachments (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  message_id uuid references public.messages (id) on delete cascade,
  uploader_id uuid references public.profiles (id) on delete set null,
  path text not null unique check (char_length(path) <= 256),
  kind text not null check (kind in ('image', 'video', 'voice', 'audio', 'document')),
  size_bytes bigint not null check (size_bytes > 0 and size_bytes <= 52428800),
  created_at timestamptz not null default now()
);
create index attachments_conversation_idx on public.attachments (conversation_id, created_at desc);
create index attachments_message_idx on public.attachments (message_id);
create index attachments_uploader_idx on public.attachments (uploader_id);

create table public.message_reactions (
  message_id uuid not null,
  conversation_id uuid not null,
  user_id uuid not null references public.profiles (id) on delete cascade,
  emoji text not null check (char_length(emoji) between 1 and 16),
  created_at timestamptz not null default now(),
  primary key (message_id, user_id),
  foreign key (message_id, conversation_id) references public.messages (id, conversation_id) on delete cascade
);
create index message_reactions_conversation_idx on public.message_reactions (conversation_id);
create index message_reactions_user_idx on public.message_reactions (user_id);

create table public.message_stars (
  user_id uuid not null references public.profiles (id) on delete cascade,
  message_id uuid not null,
  conversation_id uuid not null,
  created_at timestamptz not null default now(),
  primary key (user_id, message_id),
  foreign key (message_id, conversation_id) references public.messages (id, conversation_id) on delete cascade
);
create index message_stars_message_idx on public.message_stars (message_id, conversation_id);

create table public.message_hidden (
  user_id uuid not null references public.profiles (id) on delete cascade,
  message_id uuid not null,
  conversation_id uuid not null,
  created_at timestamptz not null default now(),
  primary key (user_id, message_id),
  foreign key (message_id, conversation_id) references public.messages (id, conversation_id) on delete cascade
);
create index message_hidden_conversation_idx on public.message_hidden (user_id, conversation_id);
create index message_hidden_message_idx on public.message_hidden (message_id, conversation_id);

create table public.conversation_pins (
  conversation_id uuid not null,
  message_id uuid not null,
  pinned_by uuid references public.profiles (id) on delete set null,
  pinned_at timestamptz not null default now(),
  primary key (conversation_id, message_id),
  foreign key (message_id, conversation_id) references public.messages (id, conversation_id) on delete cascade
);
create index conversation_pins_message_idx on public.conversation_pins (message_id, conversation_id);
create index conversation_pins_pinned_by_idx on public.conversation_pins (pinned_by);

-- Statuses (24 hour updates) ---------------------------------------------
create table public.statuses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references public.profiles (id) on delete cascade,
  kind text not null check (kind in ('text', 'image', 'video')),
  body text check (char_length(body) <= 700),
  background text check (background ~ '^#[0-9A-Fa-f]{6}$'),
  font smallint not null default 0 check (font between 0 and 4),
  media_path text check (char_length(media_path) <= 256),
  caption text check (char_length(caption) <= 700),
  duration_ms integer check (duration_ms between 0 and 60000),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '24 hours'),
  constraint statuses_content check ((kind = 'text' and body is not null) or (kind <> 'text' and media_path is not null)),
  constraint statuses_ttl check (expires_at <= created_at + interval '24 hours')
);
create index statuses_user_expires_idx on public.statuses (user_id, expires_at);
create index statuses_expires_idx on public.statuses (expires_at);
create index statuses_media_path_idx on public.statuses (media_path) where media_path is not null;

create table public.status_views (
  status_id uuid not null references public.statuses (id) on delete cascade,
  viewer_id uuid not null default auth.uid() references public.profiles (id) on delete cascade,
  viewed_at timestamptz not null default now(),
  reaction text check (char_length(reaction) <= 16),
  primary key (status_id, viewer_id)
);
create index status_views_viewer_idx on public.status_views (viewer_id);

create table public.status_mutes (
  user_id uuid not null default auth.uid() references public.profiles (id) on delete cascade,
  muted_user_id uuid not null references public.profiles (id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, muted_user_id),
  check (user_id <> muted_user_id)
);
create index status_mutes_muted_idx on public.status_mutes (muted_user_id);

-- Calls -------------------------------------------------------------------
create table public.calls (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references public.conversations (id) on delete set null,
  initiator_id uuid references public.profiles (id) on delete set null,
  media text not null check (media in ('audio', 'video')),
  status text not null default 'ringing' check (status in ('ringing', 'active', 'ended', 'missed', 'declined', 'busy', 'failed', 'cancelled')),
  created_at timestamptz not null default now(),
  answered_at timestamptz,
  ended_at timestamptz,
  end_reason text check (char_length(end_reason) <= 32)
);
create index calls_conversation_idx on public.calls (conversation_id, created_at desc);
create index calls_initiator_idx on public.calls (initiator_id);
create index calls_ringing_idx on public.calls (created_at) where status in ('ringing', 'active');

create table public.call_participants (
  call_id uuid not null references public.calls (id) on delete cascade,
  user_id uuid not null references public.profiles (id) on delete cascade,
  role text not null check (role in ('caller', 'callee')),
  state text not null default 'invited' check (state in ('invited', 'joined', 'declined', 'missed', 'left', 'busy')),
  joined_at timestamptz,
  left_at timestamptz,
  primary key (call_id, user_id)
);
create index call_participants_user_idx on public.call_participants (user_id, call_id);

-- Safety ------------------------------------------------------------------
create table public.reports (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid default auth.uid() references public.profiles (id) on delete set null,
  reported_user_id uuid references public.profiles (id) on delete set null,
  conversation_id uuid references public.conversations (id) on delete set null,
  reason text not null check (reason in ('spam', 'harassment', 'inappropriate', 'impersonation', 'scam', 'other')),
  details text check (char_length(details) <= 1000),
  evidence jsonb check (evidence is null or pg_column_size(evidence) <= 65536),
  status text not null default 'open' check (status in ('open', 'reviewing', 'closed')),
  created_at timestamptz not null default now(),
  check (reported_user_id is not null or conversation_id is not null)
);
create index reports_reporter_idx on public.reports (reporter_id);
create index reports_reported_user_idx on public.reports (reported_user_id);
create index reports_conversation_idx on public.reports (conversation_id);

-- Server-only bookkeeping (no client policies) -----------------------------
create table public.storage_cleanup_queue (
  id bigint generated always as identity primary key,
  bucket text not null,
  path text not null,
  enqueued_at timestamptz not null default now(),
  attempts integer not null default 0
);

create table public.app_secrets (
  key text primary key,
  value text not null
);

-- Read models -------------------------------------------------------------
create view public.group_members with (security_invoker = true) as
select m.conversation_id as group_id, m.user_id, m.role, m.added_by, m.joined_at
from public.conversation_members m
join public.groups g on g.conversation_id = m.conversation_id;

-- Receipts are stored as per-member watermarks (one write per read event
-- instead of one per message); this view expands them per message.
create view public.message_receipts with (security_invoker = true) as
select msg.id as message_id, msg.conversation_id, m.user_id,
       (coalesce(m.delivered_up_to, m.read_up_to) >= msg.created_at) as delivered,
       (m.read_up_to >= msg.created_at) as read
from public.messages msg
join public.conversation_members m
  on m.conversation_id = msg.conversation_id and m.user_id is distinct from msg.sender_id;

-- Row level security is enabled on every table; policies follow.
alter table public.profiles enable row level security;
alter table public.user_privacy_settings enable row level security;
alter table public.status_audience_list enable row level security;
alter table public.user_notification_settings enable row level security;
alter table public.user_contacts enable row level security;
alter table public.user_blocks enable row level security;
alter table public.user_devices enable row level security;
alter table public.notification_tokens enable row level security;
alter table public.communities enable row level security;
alter table public.community_members enable row level security;
alter table public.conversations enable row level security;
alter table public.conversation_members enable row level security;
alter table public.conversation_member_state enable row level security;
alter table public.groups enable row level security;
alter table public.messages enable row level security;
alter table public.attachments enable row level security;
alter table public.message_reactions enable row level security;
alter table public.message_stars enable row level security;
alter table public.message_hidden enable row level security;
alter table public.conversation_pins enable row level security;
alter table public.statuses enable row level security;
alter table public.status_views enable row level security;
alter table public.status_mutes enable row level security;
alter table public.calls enable row level security;
alter table public.call_participants enable row level security;
alter table public.reports enable row level security;
alter table public.storage_cleanup_queue enable row level security;
alter table public.app_secrets enable row level security;
