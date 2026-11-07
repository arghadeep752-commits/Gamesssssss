// Email sign-in with Hime's own 6-digit codes.
//
//   {action:"config"}                              -> { otp: boolean }
//   {action:"send_code", email}                    -> emails a 6-digit code
//   {action:"verify_code", email, code, password?} -> { token_hash } to finish sign-in
//   {action:"signup", email, password}             -> creates an account (only while
//                                                     email codes are not configured)
//
// Codes are sent through the SMTP account in the SMTP_USER / SMTP_PASS secrets
// (e.g. a Gmail address + App password), so Supabase's built-in mailer, its
// link-only templates and its tiny hourly limit are not involved.
import { adminClient, corsHeaders, json } from "../_shared/http.ts";

const admin = adminClient();

const smtp = {
  host: Deno.env.get("SMTP_HOST") ?? "smtp.gmail.com",
  port: Number(Deno.env.get("SMTP_PORT") ?? "465"),
  user: (Deno.env.get("SMTP_USER") ?? "").trim(),
  pass: (Deno.env.get("SMTP_PASS") ?? "").replace(/\s+/g, ""),
  name: Deno.env.get("SMTP_SENDER_NAME") ?? "Hime",
};
const smtpReady = () => smtp.user.includes("@") && smtp.pass.length >= 8;

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

function normEmail(v: unknown): string | null {
  const e = String(v ?? "").trim().toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e) && e.length <= 254 ? e : null;
}

function strongPassword(p: string): boolean {
  return p.length >= 8 && p.length <= 72 && /[A-Za-z]/.test(p) && /[0-9]/.test(p);
}

function newCode(): string {
  // Rejection sampling: uniform over 000000-999999.
  const buf = new Uint32Array(1);
  while (true) {
    crypto.getRandomValues(buf);
    if (buf[0] < 4_294_000_000) return String(buf[0] % 1_000_000).padStart(6, "0");
  }
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

// ------------------------------------------------------------------ SMTP (implicit TLS, port 465)
async function sendMail(to: string, subject: string, text: string, html: string): Promise<void> {
  const conn = await Deno.connectTls({ hostname: smtp.host, port: smtp.port });
  const enc = new TextEncoder();
  const dec = new TextDecoder();
  const reader = conn.readable.getReader();
  const writer = conn.writable.getWriter();
  let buf = "";

  const reply = async (): Promise<string> => {
    while (true) {
      const lines = buf.split("\r\n");
      for (let i = 0; i < lines.length - 1; i++) {
        if (/^\d{3} /.test(lines[i])) {
          const out = lines.slice(0, i + 1).join("\n");
          buf = lines.slice(i + 1).join("\r\n");
          return out;
        }
      }
      const { value, done } = await reader.read();
      if (done) throw new Error("smtp connection closed");
      buf += dec.decode(value, { stream: true });
    }
  };
  const command = async (line: string, ok: number[], label = line.split(" ")[0]): Promise<string> => {
    await writer.write(enc.encode(line + "\r\n"));
    const r = await reply();
    if (!ok.includes(Number(r.slice(0, 3)))) throw new Error(`smtp ${label} failed: ${r.slice(0, 200)}`);
    return r;
  };

  try {
    const greeting = await reply();
    if (!greeting.startsWith("220")) throw new Error(`smtp greeting: ${greeting.slice(0, 200)}`);
    await command("EHLO hime.app", [250]);
    await command("AUTH LOGIN", [334]);
    await command(btoa(smtp.user), [334], "AUTH-USER");
    await command(btoa(smtp.pass), [235], "AUTH-PASS");
    await command(`MAIL FROM:<${smtp.user}>`, [250]);
    await command(`RCPT TO:<${to}>`, [250, 251]);
    await command("DATA", [354]);
    const boundary = "hime-" + crypto.randomUUID().replaceAll("-", "");
    const message = [
      `From: ${smtp.name} <${smtp.user}>`,
      `To: <${to}>`,
      `Subject: ${subject}`,
      `Date: ${new Date().toUTCString()}`,
      `Message-ID: <${crypto.randomUUID()}@hime.app>`,
      "MIME-Version: 1.0",
      `Content-Type: multipart/alternative; boundary="${boundary}"`,
      "",
      `--${boundary}`,
      "Content-Type: text/plain; charset=UTF-8",
      "Content-Transfer-Encoding: 7bit",
      "",
      text,
      "",
      `--${boundary}`,
      "Content-Type: text/html; charset=UTF-8",
      "Content-Transfer-Encoding: 7bit",
      "",
      html,
      "",
      `--${boundary}--`,
      "",
    ].join("\r\n").replace(/\r\n\./g, "\r\n..");
    await writer.write(enc.encode(message + "\r\n.\r\n"));
    const done = await reply();
    if (!done.startsWith("250")) throw new Error(`smtp DATA rejected: ${done.slice(0, 200)}`);
    await writer.write(enc.encode("QUIT\r\n")).catch(() => {});
  } finally {
    try {
      conn.close();
    } catch {
      // already closed
    }
  }
}

function codeEmail(code: string): { subject: string; text: string; html: string } {
  const spaced = `${code.slice(0, 3)} ${code.slice(3)}`;
  return {
    subject: `${code} is your Hime code`,
    text: `Your Hime code is ${code}\n\nEnter it in the Hime app. It expires in 10 minutes.\nIf you didn't ask for this code, you can ignore this email.`,
    html: `<div style="font-family:Arial,sans-serif;max-width:420px;margin:auto;padding:24px;color:#202124">
<div style="font-size:22px;font-weight:bold;margin-bottom:8px">Hime</div>
<p style="font-size:15px">Your sign-in code is:</p>
<div style="font-size:36px;font-weight:bold;letter-spacing:6px;background:#F5D547;border-radius:12px;padding:14px 0;text-align:center">${spaced}</div>
<p style="font-size:13px;color:#777777">Enter it in the Hime app. It expires in 10 minutes. If you didn't ask for this code, you can ignore this email.</p>
</div>`,
  };
}

// ------------------------------------------------------------------ actions
async function sendCode(body: Record<string, unknown>, ip: string): Promise<Response> {
  const email = normEmail(body.email);
  if (!email) return json({ error: "invalid_email" }, 400);
  if (!smtpReady()) return json({ error: "email_not_configured" }, 503);

  const { data: last } = await admin.from("auth_email_codes").select("created_at")
    .eq("email", email).order("created_at", { ascending: false }).limit(1).maybeSingle();
  if (last) {
    const age = Date.now() - Date.parse(last.created_at as string);
    if (age < RESEND_AFTER_MS) return json({ error: "wait", seconds: Math.ceil((RESEND_AFTER_MS - age) / 1000) }, 429);
  }
  if (!(await allow(`send:${email}`, 6, 3600)) || !(await allow(`ip:${ip}`, 30, 3600))) {
    return json({ error: "rate_limited" }, 429);
  }

  const code = newCode();
  const { error } = await admin.from("auth_email_codes").insert({
    email,
    code_hash: await sha256(`${await pepper()}:${email}:${code}`),
    expires_at: new Date(Date.now() + CODE_TTL_MS).toISOString(),
    ip,
  });
  if (error) throw error;

  const mail = codeEmail(code);
  try {
    await sendMail(email, mail.subject, mail.text, mail.html);
  } catch (e) {
    console.error("send failed", e);
    return json({ error: "send_failed" }, 502);
  }

  // Housekeeping: drop day-old codes and limiter rows.
  const dayAgo = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
  await admin.from("auth_email_codes").delete().lt("created_at", dayAgo);
  await admin.from("auth_rate_events").delete().lt("created_at", dayAgo);
  return json({ ok: true, expires_in: CODE_TTL_MS / 1000 });
}

async function verifyCode(body: Record<string, unknown>): Promise<Response> {
  const email = normEmail(body.email);
  const code = String(body.code ?? "").replace(/\D/g, "");
  const password = body.password == null || body.password === "" ? null : String(body.password);
  if (!email || code.length !== 6) return json({ error: "invalid_code" }, 400);
  if (password !== null && !strongPassword(password)) return json({ error: "weak_password" }, 400);
  if (!(await allow(`verify:${email}`, 20, 3600))) return json({ error: "rate_limited" }, 429);

  const { data: row } = await admin.from("auth_email_codes").select("id, code_hash, attempts, expires_at")
    .eq("email", email).is("used_at", null).order("created_at", { ascending: false }).limit(1).maybeSingle();
  if (!row || Date.parse(row.expires_at as string) < Date.now()) return json({ error: "code_expired" }, 400);
  if ((row.attempts as number) >= MAX_ATTEMPTS) return json({ error: "too_many_attempts" }, 429);

  const hash = await sha256(`${await pepper()}:${email}:${code}`);
  if (!sameHash(hash, row.code_hash as string)) {
    await admin.from("auth_email_codes").update({ attempts: (row.attempts as number) + 1 }).eq("id", row.id);
    return json({ error: "invalid_code" }, 400);
  }
  await admin.from("auth_email_codes").update({ used_at: new Date().toISOString() }).eq("id", row.id);

  // The code proves the person owns this address: create or unlock the account.
  const { data: found, error: findErr } = await admin.rpc("auth_user_by_email", { p_email: email });
  if (findErr) throw findErr;
  const existing = (found as { id: string; confirmed: boolean }[] | null)?.[0];
  if (!existing) {
    const { error } = await admin.auth.admin.createUser({ email, email_confirm: true, ...(password ? { password } : {}) });
    if (error) throw error;
  } else {
    const attrs: Record<string, unknown> = {};
    if (!existing.confirmed) attrs.email_confirm = true;
    if (password) attrs.password = password;
    if (Object.keys(attrs).length > 0) {
      const { error } = await admin.auth.admin.updateUserById(existing.id, attrs);
      if (error) throw error;
    }
  }

  // A one-time sign-in token for this user; no email is sent by generateLink.
  const { data: link, error: linkErr } = await admin.auth.admin.generateLink({ type: "magiclink", email });
  if (linkErr || !link?.properties?.hashed_token) throw linkErr ?? new Error("no token");
  return json({ token_hash: link.properties.hashed_token, type: "magiclink" });
}

async function signup(body: Record<string, unknown>, ip: string): Promise<Response> {
  if (smtpReady()) return json({ error: "verification_required" }, 400);
  const email = normEmail(body.email);
  const password = String(body.password ?? "");
  if (!email) return json({ error: "invalid_email" }, 400);
  if (!strongPassword(password)) return json({ error: "weak_password" }, 400);
  if (!(await allow(`signup:${ip}`, 10, 3600))) return json({ error: "rate_limited" }, 429);
  const { data: found } = await admin.rpc("auth_user_by_email", { p_email: email });
  if ((found as unknown[] | null)?.length) return json({ error: "email_exists" }, 409);
  const { error } = await admin.auth.admin.createUser({ email, password, email_confirm: true });
  if (error) {
    if (/already/i.test(error.message)) return json({ error: "email_exists" }, 409);
    throw error;
  }
  return json({ ok: true });
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
      case "config":
        return json({ otp: smtpReady() });
      case "send_code":
        return await sendCode(body, ip);
      case "verify_code":
        return await verifyCode(body);
      case "signup":
        return await signup(body, ip);
      default:
        return json({ error: "bad_request" }, 400);
    }
  } catch (e) {
    console.error("email-auth", e);
    return json({ error: "server_error" }, 500);
  }
});
