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

## Phone-number sign-in (free SMS codes)

Hime signs people in with their phone number and a 6-digit SMS code (`phone-auth` edge function,
migration `0017_phone_codes`). No paid SMS provider is used: an Android phone runs the free,
open-source **SMS Gateway for Android** app (<https://sms-gate.app>) and sends the codes from its own
SIM, using the SIM's SMS pack (most Indian plans include 100 free SMS a day).

1. Install SMS Gateway for Android on a phone with a SIM that has an SMS pack, open it, switch on
   **Cloud server**, and start the service. Its *Cloud server* section shows a **username** and **password**.
2. Store them for the function (service-role-only table):
   `insert into public.app_secrets(key, value) values ('sms_gateway_user','…'),('sms_gateway_pass','…')
    on conflict (key) do update set value = excluded.value;`
3. Keep that phone online (allow the app to run in the background / ignore battery optimisation).

Settings in `app_secrets`: `sms_allowed_prefixes` (default `+91`; `*` for all countries — international
SMS is not free), `sms_daily_cap` (default 90 texts/day), `sms_sim_number` (1 or 2: which SIM sends on a
dual-SIM phone). Codes are queued with a 10-minute expiry and high priority; if the gateway phone hasn't
picked a text up within ~7 seconds the function logs it as queued (phone asleep or offline). Limits per number: 1 code/minute, 5/hour, 10/day;
codes expire after 10 minutes and allow 5 tries.

Phone-only accounts get a private placeholder address (`p<number>-<random>@phone.hime.invalid`) because
Supabase issues sign-in tokens for an email address; it is never shown and never receives mail. Accounts
made earlier with an email can add a number in *Settings → Account → Add your phone number* and then sign
in with it. While the SMS sender isn't set up, the welcome screen also offers "Use email instead".

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
