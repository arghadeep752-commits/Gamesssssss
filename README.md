# Hime — Connect Without Limits.

Private, real-time messaging and calling for Android, built with Flutter and Supabase.
Made with love in India 🇮🇳

## What's inside

| Area | Highlights |
| --- | --- |
| Messaging | One-to-one and group chats, replies, forwarding, edit (15 min), delete for me / everyone, reactions, emoji, stars, pins, mute, archive, search (on device), link previews, export chat |
| Media | Photos, videos, voice messages with waveform, documents, contacts, location — encrypted per file, chunked, with real upload/download progress |
| Delivery | Optimistic sending with an offline outbox, sent / delivered / read ticks, typing indicators, online and last seen (privacy-aware) |
| Calls | One-to-one WebRTC voice and video calls, STUN/TURN, adaptive bitrate, reconnection, speaker / Bluetooth routing, picture-in-picture, foreground service, call history |
| Groups & communities | Admins, permissions, invite links + QR, announcement groups, community sub-groups |
| Status | Text, photo and video updates that expire after 24 h, viewers list, reactions and replies, audience controls |
| Privacy | End-to-end encryption, per-field visibility, read-receipt toggle, blocking, reporting, contact discovery by hashed numbers, data export, account deletion |
| Security | X25519 + HKDF + ChaCha20-Poly1305 via `package:cryptography`, safety numbers, two-step verification (TOTP), encrypted local database, row-level security everywhere |

## Repository layout

```
lib/                     Flutter app
  core/                  theme, widgets, config, formatting
  services/              session, realtime hub, presence, E2EE, local DB, notifications
  features/              auth, chats, calls, groups, communities, status, contacts, settings…
supabase/functions/      Edge functions (ICE servers, push, delete account, cleanup)
supabase/migrations/     Database schema, RLS, RPCs, realtime and storage policies
android_overlay/         Manifest, Kotlin call glue, icons and splash merged into the generated Android project
tool/ci/patch_android.py Applies the overlay after `flutter create`
.github/workflows/       CI: analyze, test, build signed APKs, publish releases
docs/                    Setup, architecture & API, security model, privacy policy, terms
test/                    Crypto, formatting and widget tests
```

## Quick start

1. Install Flutter 3.47+ and Android SDK 36.
2. `flutter create --platforms=android --org app --project-name hime --no-pub .`
3. `python3 tool/ci/patch_android.py`
4. `flutter pub get && flutter run`

The app talks to the Supabase project configured in `assets/config/hime.json`
(URL + publishable key — safe to ship; all access is enforced by row-level security).
See [docs/SETUP.md](docs/SETUP.md) to run your own backend, enable push notifications and TURN relays.

## Docs

- [Setup & deployment](docs/SETUP.md)
- [Architecture & API](docs/API.md)
- [Security model](docs/SECURITY.md)
- [Privacy policy](docs/PRIVACY_POLICY.md) · [Terms](docs/TERMS.md)
