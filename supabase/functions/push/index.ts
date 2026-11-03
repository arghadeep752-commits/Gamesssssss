// Sends Firebase Cloud Messaging data pushes for new messages and calls.
// Message contents are end-to-end encrypted, so pushes only ever carry
// metadata (who, which chat, what kind) — never the text itself.
//
// Requires the secret FCM_SERVICE_ACCOUNT (the JSON of a Firebase service
// account with the "Firebase Cloud Messaging API Admin" role). Without it
// the function answers { configured: false } and the app relies on its
// realtime connection while it is running.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { adminClient, corsHeaders, handleError, HttpError, json, requireUser } from "../_shared/http.ts";

type ServiceAccount = { client_email: string; private_key: string; project_id: string };

let cachedToken: { token: string; expires: number } | null = null;

function b64url(data: ArrayBuffer | Uint8Array | string): string {
  const bytes = typeof data === "string" ? new TextEncoder().encode(data) : new Uint8Array(data);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function accessToken(sa: ServiceAccount): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  if (cachedToken && cachedToken.expires > now + 60) return cachedToken.token;
  const header = b64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claims = b64url(JSON.stringify({
    iss: sa.client_email,
    scope: "https://www.googleapis.com/auth/firebase.messaging",
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
  }));
  const pem = sa.private_key.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  const der = Uint8Array.from(atob(pem), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey(
    "pkcs8",
    der,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(`${header}.${claims}`));
  const assertion = `${header}.${claims}.${b64url(signature)}`;
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion }),
  });
  if (!res.ok) throw new Error(`oauth_${res.status}: ${await res.text()}`);
  const body = await res.json();
  cachedToken = { token: body.access_token, expires: now + (body.expires_in ?? 3600) };
  return cachedToken.token;
}

const KIND_LABEL: Record<string, string> = {
  text: "New message",
  image: "📷 Photo",
  video: "🎥 Video",
  voice: "🎤 Voice message",
  audio: "🎵 Audio",
  document: "📄 Document",
  contact: "👤 Contact",
  location: "📍 Location",
};

type Target = { userId: string; title: string; body: string };

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
  try {
    const admin = adminClient();
    const { user } = await requireUser(req, admin);
    const raw = Deno.env.get("FCM_SERVICE_ACCOUNT");
    if (!raw) return json({ configured: false, sent: 0 });
    const sa = JSON.parse(raw) as ServiceAccount;
    const input = await req.json().catch(() => ({}));
    const type = String(input.type ?? "");

    let targets: Target[] = [];
    let data: Record<string, string> = {};
    let ttl = "600s";

    if (type === "message") {
      const { data: msg } = await admin.from("messages")
        .select("id, conversation_id, sender_id, kind, created_at, hidden_for_recipients")
        .eq("id", String(input.message_id ?? "")).maybeSingle();
      if (!msg || msg.sender_id !== user.id) throw new HttpError(403, "not_sender");
      if (Date.now() - Date.parse(msg.created_at) > 5 * 60 * 1000) throw new HttpError(409, "too_old");
      if (msg.hidden_for_recipients) return json({ configured: true, sent: 0 });

      const [{ data: conv }, { data: group }, { data: sender }, { data: members }] = await Promise.all([
        admin.from("conversations").select("id, type").eq("id", msg.conversation_id).single(),
        admin.from("groups").select("name").eq("conversation_id", msg.conversation_id).maybeSingle(),
        admin.from("profiles").select("display_name, username").eq("id", user.id).single(),
        admin.from("conversation_members").select("user_id").eq("conversation_id", msg.conversation_id).neq("user_id", user.id),
      ]);
      const ids = (members ?? []).map((m) => m.user_id as string);
      if (ids.length === 0) return json({ configured: true, sent: 0 });
      const [{ data: states }, { data: prefs }] = await Promise.all([
        admin.from("conversation_member_state").select("user_id, muted_until")
          .eq("conversation_id", msg.conversation_id).in("user_id", ids),
        admin.from("user_notification_settings").select("user_id, messages, groups, show_preview").in("user_id", ids),
      ]);
      const muted = new Set((states ?? [])
        .filter((s) => s.muted_until && Date.parse(s.muted_until) > Date.now())
        .map((s) => s.user_id as string));
      const senderName = sender?.display_name || sender?.username || "Someone";
      const isGroup = conv?.type === "group";
      for (const p of prefs ?? []) {
        if (muted.has(p.user_id)) continue;
        if (isGroup ? !p.groups : !p.messages) continue;
        const label = KIND_LABEL[msg.kind] ?? "New message";
        targets.push({
          userId: p.user_id,
          title: p.show_preview ? (isGroup ? (group?.name ?? "Group") : senderName) : "Hime",
          body: p.show_preview ? (isGroup ? `${senderName}: ${label}` : label) : "New message",
        });
      }
      data = { type: "message", conversation_id: msg.conversation_id, message_id: msg.id };
    } else if (type === "call" || type === "missed_call") {
      const { data: call } = await admin.from("calls")
        .select("id, conversation_id, initiator_id, media, status, created_at")
        .eq("id", String(input.call_id ?? "")).maybeSingle();
      if (!call || call.initiator_id !== user.id) throw new HttpError(403, "not_caller");
      if (type === "call" && call.status !== "ringing") return json({ configured: true, sent: 0 });
      if (type === "missed_call" && !["missed", "cancelled"].includes(call.status)) return json({ configured: true, sent: 0 });
      const [{ data: sender }, { data: parts }] = await Promise.all([
        admin.from("profiles").select("display_name, username").eq("id", user.id).single(),
        admin.from("call_participants").select("user_id").eq("call_id", call.id).neq("user_id", user.id),
      ]);
      const ids = (parts ?? []).map((p) => p.user_id as string);
      const { data: prefs } = await admin.from("user_notification_settings").select("user_id, calls").in("user_id", ids);
      const name = sender?.display_name || sender?.username || "Someone";
      for (const p of prefs ?? []) {
        if (!p.calls) continue;
        targets.push({
          userId: p.user_id,
          title: name,
          body: type === "call"
            ? (call.media === "video" ? "Incoming video call" : "Incoming voice call")
            : (call.media === "video" ? "Missed video call" : "Missed voice call"),
        });
      }
      data = {
        type,
        call_id: call.id,
        conversation_id: call.conversation_id ?? "",
        media: call.media,
        caller_id: user.id,
        caller_name: name,
      };
      if (type === "call") ttl = "45s";
    } else {
      throw new HttpError(400, "unknown_type");
    }

    if (targets.length === 0) return json({ configured: true, sent: 0 });
    const { data: tokens } = await admin.from("notification_tokens")
      .select("token, user_id").in("user_id", targets.map((t) => t.userId));
    const byUser = new Map(targets.map((t) => [t.userId, t]));
    const token = await accessToken(sa);
    let sent = 0;
    const stale: string[] = [];
    await Promise.all((tokens ?? []).map(async (t) => {
      const target = byUser.get(t.user_id);
      if (!target) return;
      const res = await fetch(`https://fcm.googleapis.com/v1/projects/${sa.project_id}/messages:send`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          message: {
            token: t.token,
            data: { ...data, title: target.title, body: target.body },
            android: { priority: "HIGH", ttl },
          },
        }),
      });
      if (res.ok) {
        sent++;
      } else if (res.status === 404 || res.status === 400) {
        const text = await res.text();
        if (text.includes("UNREGISTERED") || text.includes("INVALID_ARGUMENT")) stale.push(t.token);
      }
    }));
    if (stale.length > 0) await admin.from("notification_tokens").delete().in("token", stale);
    return json({ configured: true, sent });
  } catch (e) {
    return handleError(e);
  }
});
