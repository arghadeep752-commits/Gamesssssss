// Phone-number sign-in with Hime's own 6-digit SMS codes.
//
//   {action:"config"}                    -> { sms: boolean, prefixes: string[] }
//   {action:"send_code", phone}          -> texts a 6-digit code to the number
//   {action:"verify_code", phone, code}  -> { token_hash, type } to finish signing in
//                                           (creates the account on first sign-in)
//   {action:"link", phone, code}         -> adds or changes the phone number of the
//                                           signed-in account (needs its access token)
//
// The texts are sent free of charge: an Android phone runs the free, open-source
// "SMS Gateway for Android" app (https://sms-gate.app). This function calls that
// app's cloud API and the phone sends the SMS from its own SIM, using the SIM's
// SMS pack. No paid SMS provider is involved. Its username/password live in the
// service-role-only app_secrets table (sms_gateway_user / sms_gateway_pass) or in
// the SMS_GATEWAY_USER / SMS_GATEWAY_PASS function secrets.
import { adminClient, corsHeaders, HttpError, json, requireUser } from "../_shared/http.ts";

const admin = adminClient();

type Gateway = { url: string; user: string; pass: string; prefixes: string[]; dailyCap: number; sim: number | null };
let gwCache: { at: number; value: Gateway } | null = null;
async function gateway(): Promise<Gateway> {
  if (gwCache && Date.now() - gwCache.at < 60_000) return gwCache.value;
  const env = (k: string) => (Deno.env.get(k) ?? "").trim();
  const { data } = await admin.from("app_secrets").select("key, value")
    .in("key", ["sms_gateway_url", "sms_gateway_user", "sms_gateway_pass", "sms_allowed_prefixes", "sms_daily_cap", "sms_sim_number"]);
  const db = Object.fromEntries((data ?? []).map((r) => [r.key as string, String(r.value ?? "").trim()]));
  const value: Gateway = {
    url: (env("SMS_GATEWAY_URL") || db.sms_gateway_url || "https://api.sms-gate.app/3rdparty/v1").replace(/\/+$/, ""),
    user: env("SMS_GATEWAY_USER") || db.sms_gateway_user || "",
    pass: env("SMS_GATEWAY_PASS") || db.sms_gateway_pass || "",
    prefixes: (env("SMS_ALLOWED_PREFIXES") || db.sms_allowed_prefixes || "+91").split(",").map((s) => s.trim()).filter(Boolean),
    dailyCap: Number(env("SMS_DAILY_CAP") || db.sms_daily_cap || "90") || 90,
    // Which SIM sends the texts on a dual-SIM phone (1 or 2); empty = the phone's default.
    sim: Number(env("SMS_SIM_NUMBER") || db.sms_sim_number || "0") || null,
  };
  gwCache = { at: Date.now(), value };
  return value;
}
const gatewayReady = (g: Gateway) => g.user.length > 0 && g.pass.length > 0;

const CODE_TTL_MS = 10 * 60 * 1000;
const RESEND_AFTER_MS = 60 * 1000;
const MAX_ATTEMPTS = 5;

let pepperCache: string | null = null;
async function pepper(): Promise<string> {
  if (pepperCache) return pepperCache;
  const { data, error } = await admin.from("app_secrets").select("value").eq("key", "otp_pepper").single();
  if (error || !data) throw new Error("otp pepper missing");
  pepperCache = data.value as string;
  return pepperCache;
}

async function sha256(s: string): Promise<string> {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(d)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function sameHash(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

/** E.164 ("+919876543210"), or null if it can't be a real number. */
function normPhone(v: unknown): string | null {
  const d = String(v ?? "").replace(/\D/g, "");
  if (d.length < 8 || d.length > 15 || d.startsWith("0")) return null;
  const e164 = `+${d}`;
  // Indian mobile numbers: +91 followed by 10 digits starting with 6-9.
  if (e164.startsWith("+91") && !/^\+91[6-9]\d{9}$/.test(e164)) return null;
  return e164;
}

function allowedCountry(g: Gateway, phone: string): boolean {
  return g.prefixes.includes("*") || g.prefixes.some((p) => phone.startsWith(p.startsWith("+") ? p : `+${p}`));
}

function newCode(): string {
  // Rejection sampling: uniform over 000000-999999.
  const buf = new Uint32Array(1);
  while (true) {
    crypto.getRandomValues(buf);
    if (buf[0] < 4_294_000_000) return String(buf[0] % 1_000_000).padStart(6, "0");
  }
}

function randomHex(bytes: number): string {
  const b = crypto.getRandomValues(new Uint8Array(bytes));
  return Array.from(b).map((x) => x.toString(16).padStart(2, "0")).join("");
}

/** Sliding-window limiter backed by auth_rate_events. */
async function allow(bucket: string, limit: number, windowSec: number): Promise<boolean> {
  const since = new Date(Date.now() - windowSec * 1000).toISOString();
  const { count } = await admin.from("auth_rate_events").select("id", { count: "exact", head: true })
    .eq("bucket", bucket).gte("created_at", since);
  if ((count ?? 0) >= limit) return false;
  await admin.from("auth_rate_events").insert({ bucket });
  return true;
}

const gwHeaders = (g: Gateway) => ({ "Content-Type": "application/json", Authorization: "Basic " + btoa(`${g.user}:${g.pass}`) });

/**
 * Queues the SMS on the gateway, then watches it for a few seconds.
 * Returns "sent" once the phone has picked it up, "queued" if the phone hasn't
 * fetched it yet (offline / asleep), and throws if the phone reports a failure.
 */
async function sendSms(g: Gateway, to: string, text: string): Promise<"sent" | "queued"> {
  const res = await fetch(`${g.url}/messages`, {
    method: "POST",
    headers: gwHeaders(g),
    body: JSON.stringify({
      textMessage: { text },
      phoneNumbers: [to],
      ...(g.sim ? { simNumber: g.sim } : {}),
      ttl: 600, // a code is useless after 10 minutes: don't send it late
      priority: 100, // send right away, skipping the app's send delays
    }),
    signal: AbortSignal.timeout(15_000),
  });
  if (!res.ok) throw new Error(`gateway ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const id = ((await res.json().catch(() => ({}))) as { id?: string }).id;
  if (!id) return "queued";
  for (let i = 0; i < 5; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    try {
      const st = await fetch(`${g.url}/messages/${encodeURIComponent(id)}`, { headers: gwHeaders(g), signal: AbortSignal.timeout(5000) });
      if (!st.ok) continue;
      const m = (await st.json()) as { state?: string; recipients?: { state?: string; error?: string }[] };
      const state = m.recipients?.[0]?.state ?? m.state ?? "Pending";
      if (state === "Failed") throw new Error(`phone failed to send: ${m.recipients?.[0]?.error ?? "unknown"}`);
      if (state !== "Pending") return "sent";
    } catch (e) {
      if (String(e).includes("phone failed")) throw e;
    }
  }
  return "queued";
}

// ------------------------------------------------------------------ actions
async function sendCode(body: Record<string, unknown>, ip: string): Promise<Response> {
  const phone = normPhone(body.phone);
  if (!phone) return json({ error: "invalid_phone" }, 400);
  const g = await gateway();
  if (!gatewayReady(g)) return json({ error: "sms_not_configured" }, 503);
  if (!allowedCountry(g, phone)) return json({ error: "country_not_supported", prefixes: g.prefixes }, 400);

  const { data: last } = await admin.from("auth_phone_codes").select("created_at")
    .eq("phone", phone).order("created_at", { ascending: false }).limit(1).maybeSingle();
  if (last) {
    const age = Date.now() - Date.parse(last.created_at as string);
    if (age < RESEND_AFTER_MS) return json({ error: "wait", seconds: Math.ceil((RESEND_AFTER_MS - age) / 1000) }, 429);
  }
  if (
    !(await allow(`psend:${phone}`, 5, 3600)) ||
    !(await allow(`pday:${phone}`, 10, 86400)) ||
    !(await allow(`pip:${ip}`, 15, 3600))
  ) {
    return json({ error: "rate_limited" }, 429);
  }
  // Keep within the SIM's free daily SMS allowance.
  if (!(await allow("sms:all", g.dailyCap, 86400))) return json({ error: "daily_limit" }, 429);

  const code = newCode();
  const { error } = await admin.from("auth_phone_codes").insert({
    phone,
    code_hash: await sha256(`${await pepper()}:${phone}:${code}`),
    expires_at: new Date(Date.now() + CODE_TTL_MS).toISOString(),
    ip,
  });
  if (error) throw error;

  let delivery: "sent" | "queued";
  try {
    delivery = await sendSms(g, phone, `${code} is your Hime verification code. Don't share it with anyone.`);
  } catch (e) {
    console.error("sms send failed", e);
    return json({ error: "send_failed" }, 502);
  }
  if (delivery === "queued") console.warn("sms queued: the gateway phone hasn't picked it up yet");

  // Housekeeping: drop day-old codes and limiter rows.
  const dayAgo = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
  await admin.from("auth_phone_codes").delete().lt("created_at", dayAgo);
  await admin.from("auth_rate_events").delete().lt("created_at", new Date(Date.now() - 2 * 24 * 3600 * 1000).toISOString());
  return json({ ok: true, expires_in: CODE_TTL_MS / 1000, queued: delivery === "queued" });
}

/** Checks a code; returns an error response, or null when the code is right. */
async function checkCode(phone: string, code: string): Promise<Response | null> {
  if (!(await allow(`pverify:${phone}`, 20, 3600))) return json({ error: "rate_limited" }, 429);
  const { data: row } = await admin.from("auth_phone_codes").select("id, code_hash, attempts, expires_at")
    .eq("phone", phone).is("used_at", null).order("created_at", { ascending: false }).limit(1).maybeSingle();
  if (!row || Date.parse(row.expires_at as string) < Date.now()) return json({ error: "code_expired" }, 400);
  if ((row.attempts as number) >= MAX_ATTEMPTS) return json({ error: "too_many_attempts" }, 429);
  const hash = await sha256(`${await pepper()}:${phone}:${code}`);
  if (!sameHash(hash, row.code_hash as string)) {
    await admin.from("auth_phone_codes").update({ attempts: (row.attempts as number) + 1 }).eq("id", row.id);
    return json({ error: "invalid_code" }, 400);
  }
  await admin.from("auth_phone_codes").update({ used_at: new Date().toISOString() }).eq("id", row.id);
  return null;
}

type Owner = { id: string; email: string | null; phone_confirmed: boolean };
async function ownerOf(phone: string): Promise<Owner | undefined> {
  const { data, error } = await admin.rpc("auth_user_by_phone", { p_phone: phone });
  if (error) throw error;
  return (data as Owner[] | null)?.[0];
}

async function verifyCode(body: Record<string, unknown>): Promise<Response> {
  const phone = normPhone(body.phone);
  const code = String(body.code ?? "").replace(/\D/g, "");
  if (!phone || code.length !== 6) return json({ error: "invalid_code" }, 400);
  const bad = await checkCode(phone, code);
  if (bad) return bad;

  // The code proves the person owns this number: sign in, or create the account.
  // Sign-in tokens are issued for an email address, so phone-only accounts get a
  // private placeholder address that is never shown and never receives mail.
  let email: string;
  let created = false;
  const owner = await ownerOf(phone);
  if (owner) {
    const attrs: Record<string, unknown> = {};
    if (!owner.phone_confirmed) attrs.phone_confirm = true;
    email = owner.email ?? "";
    if (!email) {
      email = `p${phone.slice(1)}-${randomHex(3)}@phone.hime.invalid`;
      attrs.email = email;
      attrs.email_confirm = true;
    }
    if (Object.keys(attrs).length > 0) {
      const { error } = await admin.auth.admin.updateUserById(owner.id, attrs);
      if (error) throw error;
    }
  } else {
    email = `p${phone.slice(1)}-${randomHex(3)}@phone.hime.invalid`;
    const { error } = await admin.auth.admin.createUser({
      phone,
      phone_confirm: true,
      email,
      email_confirm: true,
      user_metadata: { signup: "phone" },
    });
    if (error) throw error;
    created = true;
  }

  const { data: link, error: linkErr } = await admin.auth.admin.generateLink({ type: "magiclink", email });
  if (linkErr || !link?.properties?.hashed_token) throw linkErr ?? new Error("no token");
  return json({ token_hash: link.properties.hashed_token, type: "magiclink", new_account: created });
}

async function linkPhone(req: Request, body: Record<string, unknown>): Promise<Response> {
  const { user } = await requireUser(req, admin);
  const phone = normPhone(body.phone);
  const code = String(body.code ?? "").replace(/\D/g, "");
  if (!phone || code.length !== 6) return json({ error: "invalid_code" }, 400);
  const bad = await checkCode(phone, code);
  if (bad) return bad;
  const owner = await ownerOf(phone);
  if (owner && owner.id !== user.id) return json({ error: "phone_in_use" }, 409);
  const { error } = await admin.auth.admin.updateUserById(user.id, { phone, phone_confirm: true });
  if (error) throw error;
  return json({ ok: true, phone });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405);
  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    return json({ error: "bad_request" }, 400);
  }
  const ip = (req.headers.get("x-forwarded-for") ?? "").split(",")[0].trim() || "unknown";
  try {
    switch (body.action) {
      case "config": {
        const g = await gateway();
        return json({ sms: gatewayReady(g), prefixes: g.prefixes });
      }
      case "send_code":
        return await sendCode(body, ip);
      case "verify_code":
        return await verifyCode(body);
      case "link":
        return await linkPhone(req, body);
      default:
        return json({ error: "bad_request" }, 400);
    }
  } catch (e) {
    if (e instanceof HttpError) return json({ error: e.message }, e.status);
    console.error("phone-auth", e);
    return json({ error: "server_error" }, 500);
  }
});
