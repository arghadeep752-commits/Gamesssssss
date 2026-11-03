# Hime security model

## Goals

- The server stores and relays messages it cannot read.
- A stolen database dump reveals who talks to whom and when, but not what was said.
- Only established primitives from audited libraries — no home-made ciphers.

## Keys

Each installation generates an **X25519 identity key pair** on first sign-in. The private key is stored with
`flutter_secure_storage` (Android Keystore-backed EncryptedSharedPreferences) and never leaves the device.
The public key is registered as a row in `user_devices`.

A random 256-bit **local vault key** (also in the Keystore) encrypts the on-device message cache (SQLite)
with ChaCha20-Poly1305.

## Messages

For each message the sender:

1. Serialises the payload (text, reply, media keys, etc.) to JSON.
2. Encrypts it once with a fresh random content key using **ChaCha20-Poly1305**. Associated data binds
   the ciphertext to `hime/v1 | conversation | message id | sender | sender device`, so it cannot be moved
   to another chat or replayed under another id.
3. Generates an ephemeral X25519 key and, for every device of every member (including the sender's own
   other devices), derives a key-encryption key with **HKDF-SHA256** over
   `DH(ephemeral, recipient) ‖ DH(sender identity, recipient)` (salt = all three public keys,
   info = `hime/v1/wrap`) and wraps the content key (ChaCha20-Poly1305, AAD = `message id | device id`).
   This matches HPKE's authenticated mode: only the recipient device can unwrap, and successful
   decryption proves the sender device's identity key was used.
4. Calls `send_message`, which checks that the wrapped keys cover exactly the conversation's current devices
   (otherwise `stale_devices`, and the client refreshes and retries) and stores ciphertext + wrapped keys.

Recipients receive only their own wrapped key (`get_messages` / `sync_messages` select it per device).

Edits re-encrypt the new text with a new content key. "Delete for everyone" erases the ciphertext and
wrapped keys on the server.

## Media

Files are encrypted on the phone before upload with a random key and nonce in 64 KB chunks
(ChaCha20-Poly1305 STREAM construction; the final chunk is flagged in the AAD so truncation is detected).
The key travels inside the encrypted message. Storage paths are scoped to the conversation and protected by
storage RLS; downloads use short-lived signed URLs.

## Calls

WebRTC media is always encrypted with DTLS-SRTP. Signalling (SDP offers/answers, ICE candidates) is
exchanged over a private Supabase Realtime channel that only the two call participants are authorised to join.
TURN relays only see encrypted SRTP packets.

## Verification

Each chat shows a **safety number** derived with SHA-512 from both users' ids and device public keys.
If two people see the same number, no key was substituted. It changes when either side adds a device.

## Server-side protections

- Every table has row-level security; clients have no direct write access to messages, memberships,
  calls or profiles of others — writes go through `SECURITY DEFINER` functions with explicit checks
  (membership, admin rights, block lists, privacy settings, rate limits).
- Functions are revoked from `anon`/`public` and granted individually to `authenticated`.
- Realtime topics (`user:<id>`, `conv:<id>`, `call:<id>`, `presence:<id>`) are private and authorised by
  policies on `realtime.messages`.
- Only the publishable key ships in the app. The service-role key exists only inside edge functions.
- Account deletion removes the auth user (cascading to their rows) and their storage objects.
- Two-step verification (TOTP) raises the session to AAL2; the app blocks access until it is verified.

## Known limitations

- **No per-message forward secrecy.** Long-term device keys protect all messages to that device; if a device key
  is extracted, past messages to that device stored on the server could be decrypted. A double-ratchet
  (Signal protocol) upgrade is the planned next step.
- Metadata (membership, timestamps, sizes, call records) is visible to the server operator.
- Status updates are protected by access control, not end-to-end encryption.
- Contact discovery compares SHA-256 hashes of phone numbers; the phone-number space is small, so hashes
  do not hide numbers from a determined server operator. Discovery is opt-out per user
  (`discoverable_by_phone`) and the address book itself is never uploaded.
- A new device can't read messages sent before it was linked (by design).
