# Setup and deployment

## 1. Backend (Supabase)

The reference deployment runs on Supabase project `xsoueofjwwfqhsawnoux` (region ap-south-1, Mumbai).
To run your own:

1. Create a Supabase project and note its URL and **publishable** key.
2. Apply the SQL in `supabase/migrations/` in filename order (Supabase CLI: `supabase db push`, or paste each file into the SQL editor).
   Migrations create the schema, row-level security, RPCs, realtime authorisation, storage buckets and the scheduled jobs (`pg_cron` + `pg_net`).
   In `0011_function_grants_and_jobs` replace the project URL in the `hime-cleanup` job with yours.
3. Deploy the edge functions:
   ```
   supabase functions deploy ice-servers
   supabase functions deploy push
   supabase functions deploy delete-account
   supabase functions deploy cleanup --no-verify-jwt
   ```
4. Dashboard settings:
   - **Authentication → URL configuration**: add `app.hime://auth-callback` to the redirect URLs.
   - **Authentication → Providers → Email**: keep "Confirm email" on. Configure a custom SMTP server for production (the built-in sender only emails your own team and is limited to a few emails per hour). Gmail works for small apps: host `smtp.gmail.com`, port `465`, your Gmail address as user and sender, and a Google *App password* (needs 2-Step Verification). Then raise **Rate Limits → emails per hour**.
   - **Authentication → Emails → Templates**: Hime signs people in with a one-time code, so the **Magic link**, **Confirm signup** and **Reset password** templates must show `{{ .Token }}` (the default templates only contain a link). Suggested subject: `{{ .Token }} is your Hime code`; body:
     ```html
     <h2>Your Hime code</h2>
     <p>Enter this code in the Hime app:</p>
     <p style="font-size:32px;font-weight:bold;letter-spacing:6px">{{ .Token }}</p>
     <p>If you didn't request this, you can ignore this email.</p>
     ```
   - **Authentication → Providers → Phone** (optional): enable and connect an SMS provider (Twilio, MessageBird, Vonage or Textlocal) for phone sign-in with OTP.
   - **Authentication → Multi-factor**: TOTP is enabled by default; the app enforces it when a user has turned it on.
   - **Realtime → Settings**: turn off "Allow public access" so only private, authorised channels work.
5. Point the app at your project in `assets/config/hime.json`, or at build time:
   `flutter build apk --dart-define=HIME_SUPABASE_URL=https://xyz.supabase.co --dart-define=HIME_SUPABASE_KEY=sb_publishable_...`

Never put the service-role / secret key in the app. Edge functions read it from their own environment.

## 2. Calls: STUN/TURN

Calls always get Google's public STUN servers. Phones behind symmetric NAT or strict firewalls also need a TURN relay.
`ice-servers` issues short-lived credentials from one of these (set as function secrets):

| Provider | Secrets |
| --- | --- |
| Cloudflare Calls TURN | `CLOUDFLARE_TURN_KEY_ID`, `CLOUDFLARE_TURN_API_TOKEN` |
| Metered.ca | `METERED_TURN_APP`, `METERED_TURN_API_KEY` |
| Your own coturn | `TURN_URLS` (comma separated), `TURN_USERNAME`, `TURN_CREDENTIAL` |

```
supabase secrets set CLOUDFLARE_TURN_KEY_ID=... CLOUDFLARE_TURN_API_TOKEN=...
```

## 3. Push notifications (Firebase Cloud Messaging)

Without push, notifications arrive while Hime is running. For background delivery and incoming-call ringing when the app is closed:

1. Create a Firebase project and add an Android app with package `app.hime`.
2. Put the Android app's config into `assets/config/hime.json`:
   ```json
   "firebase": {
     "apiKey": "...", "appId": "1:...:android:...", "messagingSenderId": "...", "projectId": "..."
   }
   ```
   (or pass it as `--dart-define=HIME_FIREBASE_JSON='{...}'`). These identifiers are public client config, not secrets.
3. Create a service account with the "Firebase Cloud Messaging API Admin" role, download its JSON key and store it as a function secret:
   `supabase secrets set FCM_SERVICE_ACCOUNT="$(cat service-account.json)"`

Push payloads never contain message text — only "new message in chat X"; the phone fetches and decrypts.

## 4. Building the Android app

CI (`.github/workflows/hime-android.yml`) runs on every push to the `hime` branch:
`flutter create` → `tool/ci/patch_android.py` → `flutter analyze` → `flutter test` → signed split APKs → GitHub release
(marked **Latest**, so <https://github.com/arghadeep752-commits/Gamesssssss/releases/latest> always has the newest APKs).

Signing: the first run generates a release keystore and keeps it in a **draft** release called `hime-signing`
(visible only to people with write access). For a production app, move it into GitHub Actions secrets
and delete that draft. Keep a backup — Android only accepts updates signed with the same key.

Local build:

```
flutter create --platforms=android --org app --project-name hime --no-pub .
python3 tool/ci/patch_android.py
flutter build apk --release --split-per-abi
```

To sign locally, create `android/key.properties` with `storeFile`, `storePassword`, `keyAlias`, `keyPassword`.

Launch screen: WhatsApp-style — the Hime logo centred and "from ARGHADEEP DAS" at the bottom, in light and dark.
The images are generated by `python3 tool/dev/make_splash.py` (Android 12+ uses `values-v31/styles.xml`,
older versions `drawable/launch_background.xml`; the Flutter `SplashScreen` in `lib/app.dart` matches both).

## 5. Operations

- **Live backend check** — `.github/workflows/hime-e2e.yml` runs `tool/e2e/realtime_check.mjs` whenever the
  migrations or the check change (or from the Actions tab). Two throwaway accounts exchange messages, receipts,
  reactions, pins, edits/deletes, statuses (text + photo), profile changes, a group and a call through the real
  RPCs, storage and private realtime topics, and every live event is confirmed on the receiving side. The accounts
  delete themselves at the end; the report is attached to the draft release `hime-e2e-logs`.
  (It creates accounts with the email-auth `signup` action, which is only available while email codes are off.)

- `hime-expire-calls` (every 5 min) closes calls that never connected.
- `hime-cleanup` (hourly) calls the `cleanup` function, which removes expired status media and blobs of deleted messages.
- Security advisors: run Supabase's database linter after schema changes.
