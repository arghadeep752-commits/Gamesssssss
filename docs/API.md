# Architecture and API

```
Flutter app (Riverpod · GoRouter · Material 3)
 ├─ SessionController ── Supabase Auth (email+password, phone OTP, PKCE links, TOTP MFA)
 ├─ HimeCore (per signed-in user)
 │   ├─ E2ee / LocalVault / MediaCrypto ── keys in Android Keystore
 │   ├─ LocalDb (sqflite, encrypted rows) ── offline cache + outbox
 │   ├─ ChatRepository ── RPCs: send / sync / edit / delete, signed-URL media
 │   ├─ RealtimeHub ── private channel user:<id>  (messages, receipts, reactions, pins, calls)
 │   ├─ PresenceService ── presence:<id> + heartbeat RPC
 │   └─ CallController ── flutter_webrtc, signalling on call:<id>, ICE from edge function
 └─ NotificationService ── local notifications + optional FCM
Supabase
 ├─ Postgres: tables + RLS + SECURITY DEFINER RPCs + triggers that fan out realtime events
 ├─ Realtime: private broadcast topics authorised by RLS on realtime.messages
 ├─ Storage: avatars, media (encrypted blobs), status
 ├─ Edge functions: ice-servers, push, delete-account, cleanup
 └─ pg_cron: expire stale calls, hourly cleanup
```

## Data model (public schema)

| Table | Purpose |
| --- | --- |
| `profiles` | display name, username, about, avatar, phone hash, onboarding flag |
| `user_devices` | one row per installation: X25519 public key, name, platform, last active |
| `user_privacy_settings` / `user_notification_settings` | per-user preferences |
| `user_contacts`, `user_blocks` | saved contacts and blocks |
| `conversations`, `conversation_members` | direct and group chats, roles, delivery/read watermarks |
| `conversation_member_state` | private per-user state: last read, mute, archive, pin, cleared |
| `groups`, `communities`, `community_members` | group metadata, permissions, invite codes |
| `messages` | ciphertext, nonce, ephemeral key, wrapped keys per device (`keys` jsonb), system events |
| `attachments` | encrypted blob paths per message (for cleanup and access control) |
| `message_reactions`, `message_stars`, `message_hidden`, `conversation_pins` | reactions, stars, delete-for-me, pins |
| `calls`, `call_participants` | call lifecycle and history |
| `statuses`, `status_views`, `status_mutes`, `status_audience_list` | 24-hour status updates |
| `notification_tokens` | FCM tokens per device |
| `reports` | abuse reports (insert-only for users) |

Views: `message_receipts` (per-member delivered/read derived from watermarks), `group_members`.

## RPCs (called with `supabase.rpc(name, params)`, all require a signed-in user)

**Identity & presence** — `register_device(p_identity_key, p_name, p_platform, p_app_version) → uuid`,
`heartbeat(p_device_id)`, `get_presence(p_user_ids)`, `get_profiles(p_ids)`, `search_users(p_query, p_limit)`,
`is_username_available(p_username)`, `match_contacts(p_hashes)`, `register_push_token(p_token, p_device_id, p_platform)`.

**Chats** — `get_or_create_direct(p_other) → uuid`, `get_chats(p_device_id)`, `get_conversation_devices(p_conversation_id)`,
`get_messages(p_conversation_id, p_device_id, p_before, p_limit)`, `sync_messages(p_device_id, p_since, p_limit)`,
`send_message(p_id, p_conversation_id, p_kind, p_ciphertext, p_nonce, p_eph_key, p_keys, p_device_id, p_attachments)`,
`edit_message(p_id, p_ciphertext, p_nonce, p_eph_key, p_keys)`, `delete_message_for_everyone(p_id)`,
`mark_delivered(p_conversation_id, p_up_to)`, `mark_all_delivered()`, `mark_read(p_conversation_id, p_up_to)`.

Errors are raised as Postgres exceptions with stable codes in the message, e.g. `stale_devices`,
`not_a_member`, `only_admins_can_send`, `you_blocked_this_contact`, `rate_limited`, `edit_window_expired`.

**Groups** — `create_group(p_name, p_description, p_member_ids, p_community_id)`, `add_group_members(p_conversation_id, p_user_ids)`,
`get_group_members(p_conversation_id)`, `update_group_info(p_conversation_id, p_name, p_description, p_avatar_path, p_remove_avatar)`,
`update_group_settings(p_conversation_id, p_only_admins_send, p_only_admins_edit_info, p_only_admins_add)`,
`set_member_role(p_conversation_id, p_user_id, p_admin)`, `get_group_invite(p_conversation_id, p_reset)`,
`preview_group_invite(p_code)`, `join_group_by_invite(p_code)`. Leaving / removing = `DELETE` on `conversation_members` (RLS-checked).

**Communities** — `create_community(p_name, p_description)`, `get_my_communities()`, `get_community(p_community_id)`,
`create_community_group(...)`, `join_community_group(p_conversation_id)`, `get_community_invite(p_community_id, p_reset)`,
`preview_community_invite(p_code)`, `join_community_by_invite(p_code)`, `update_community(...)`.

**Calls** — `start_call(p_conversation_id, p_media)`, `answer_call(p_call_id)`, `end_call(p_call_id, p_reason)`,
`get_call(p_call_id)`, `get_incoming_call()`, `get_call_history(p_limit, p_before)`.

**Status** — `get_status_feed()`, `get_status_viewers(p_status_id)`, `mark_status_viewed(p_status_id, p_reaction)`;
posting/deleting is a direct `INSERT`/`DELETE` on `statuses` (RLS-checked).

**Account** — `export_my_data()`; deletion via the `delete-account` edge function.

## Realtime topics (all private)

| Topic | Events | Who can join |
| --- | --- | --- |
| `user:<uid>` | `message`, `receipt`, `reaction`, `conversation`, `pins`, `call` (sent by DB triggers) | that user |
| `conv:<conversation_id>` | `typing` broadcast | members |
| `presence:<uid>` | presence track (online) | people allowed by the owner's privacy settings |
| `call:<call_id>` | `signal` broadcast: `ready`, `offer`, `answer`, `ice`, `video`, `hangup` | the two participants |

The client also re-syncs on reconnect, on resume and every 45 s, so missed events are recovered.

## Storage buckets (private)

| Bucket | Path | Access |
| --- | --- | --- |
| `avatars` | `users/<uid>/…`, `groups/<conversation>/…`, `communities/<id>/…` | readable per privacy settings / membership |
| `media` | `<conversation>/<message>…` (encrypted) | conversation members, via signed URLs |
| `status` | `<uid>/…` | status audience while the status is live |

## Edge functions

| Function | Auth | Purpose |
| --- | --- | --- |
| `ice-servers` | user JWT | STUN + short-lived TURN credentials |
| `push` | user JWT | sends FCM data messages for new messages / calls (no content) |
| `delete-account` | user JWT (+AAL2 if MFA) | removes uploads and the auth user |
| `cleanup` | cron key header | deletes expired status media and blobs of deleted messages |
