// End-to-end check of Hime's live backend: two throwaway accounts talk to each
// other through the same RPCs, tables, storage and private realtime topics the
// app uses, and every real-time event is confirmed on the receiving side.
// The accounts are deleted at the end. Run from the repository root:
//   node tool/e2e/realtime_check.mjs
import { readFileSync } from "node:fs";
import { randomBytes, randomUUID } from "node:crypto";
import { createClient } from "@supabase/supabase-js";

const cfg = JSON.parse(readFileSync("assets/config/hime.json", "utf8"));
const URL = cfg.supabaseUrl;
const KEY = cfg.supabasePublishableKey;

const results = [];
let failures = 0;
function check(name, ok, extra = "") {
  results.push(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? "  — " + extra : ""}`);
  if (!ok) failures++;
  console.log(results.at(-1));
}

/** Every account this run created, so all of them are deleted at the end. */
const created = [];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const b64 = (n) => randomBytes(n).toString("base64");

async function fnError(error) {
  try {
    return await error.context.text();
  } catch {
    return String(error?.message ?? error);
  }
}

async function makeUser(tag) {
  const email = `hime-e2e-${tag}-${randomBytes(4).toString("hex")}@example.com`;
  const password = `E2e-${randomBytes(9).toString("base64url")}7a`;
  const client = createClient(URL, KEY, { auth: { persistSession: false, autoRefreshToken: false } });
  const { error } = await client.functions.invoke("email-auth", { body: { action: "signup", email, password } });
  if (error) throw new Error(`signup ${tag}: ${await fnError(error)}`);
  const { data, error: e2 } = await client.auth.signInWithPassword({ email, password });
  if (e2) throw new Error(`sign in ${tag}: ${e2.message}`);
  client.realtime.setAuth(data.session.access_token);
  const id = data.user.id;
  created.push({ tag, client });
  const username = `e2e_${tag}_${randomBytes(3).toString("hex")}`;
  const { error: e3 } = await client
    .from("profiles")
    .update({ display_name: `E2E ${tag.toUpperCase()}`, username, onboarded: true })
    .eq("id", id);
  if (e3) throw new Error(`onboard ${tag}: ${e3.message}`);
  const { data: device, error: e4 } = await client.rpc("register_device", {
    p_identity_key: b64(32),
    p_name: `E2E ${tag}`,
    p_platform: "android",
    p_app_version: "e2e",
  });
  if (e4) throw new Error(`device ${tag}: ${e4.message}`);
  return { tag, email, client, id, device, events: [] };
}

/** Subscribes a channel, failing (instead of hanging) on error or after 15 s. */
function subscribed(ch, onSubscribed) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error(`subscribe timeout on ${ch.topic}`)), 15000);
    ch.subscribe(async (status, err) => {
      if (status === "SUBSCRIBED") {
        clearTimeout(t);
        try {
          if (onSubscribed) await onSubscribed();
          resolve();
        } catch (e) {
          reject(e);
        }
      } else if (status === "CHANNEL_ERROR" || status === "TIMED_OUT" || status === "CLOSED") {
        clearTimeout(t);
        reject(new Error(`${ch.topic}: ${status} ${err?.message ?? ""}`));
      }
    });
  });
}

/** Subscribes to the private user:<id> topic and records every event. */
async function listen(u) {
  const ch = u.client.channel(`user:${u.id}`, { config: { private: true } });
  for (const ev of ["message", "receipt", "reaction", "conversation", "pins", "call", "status", "status_view", "profile"]) {
    ch.on("broadcast", { event: ev }, (msg) => u.events.push({ ev, data: msg.payload?.payload ?? msg.payload }));
  }
  await subscribed(ch);
  return ch;
}

async function waitFor(u, ev, pred = () => true, ms = 10000) {
  const start = Date.now();
  while (Date.now() - start < ms) {
    const hit = u.events.find((e) => e.ev === ev && pred(e.data ?? {}));
    if (hit) return { hit, ms: Date.now() - start };
    await sleep(100);
  }
  return { hit: null, ms };
}

async function expectEvent(name, u, ev, pred) {
  const { hit, ms } = await waitFor(u, ev, pred);
  check(name, !!hit, hit ? `${ms} ms` : "no event within 10 s");
  return hit;
}

// A real 1x1 JPEG.
const JPEG = Buffer.from(
  "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q==",
  "base64",
);

async function main() {
  const A = await makeUser("a");
  const B = await makeUser("b");
  check("accounts, profiles and devices", true);
  await listen(A);
  await listen(B);
  check("private realtime topics joined", true);

  // ---- direct chat
  const { data: conv, error: e1 } = await A.client.rpc("get_or_create_direct", { p_other: B.id });
  check("open a direct chat", !e1, e1?.message);
  const keys = { [A.device]: b64(48), [B.device]: b64(48) };
  const m1 = randomUUID();
  const { error: e2 } = await A.client.rpc("send_message", {
    p_id: m1, p_conversation_id: conv, p_kind: "text", p_ciphertext: b64(40), p_nonce: b64(12), p_eph_key: b64(32),
    p_keys: keys, p_device_id: A.device,
  });
  check("send an encrypted message", !e2, e2?.message);
  const got = await expectEvent("recipient gets the message live", B, "message", (d) => d.id === m1);
  if (got) check("recipient gets only its own device key", Object.keys(got.data.keys ?? {}).join() === B.device);

  // typing indicator over the conversation topic (client to client)
  const convA = A.client.channel(`conv:${conv}`, { config: { private: true } });
  const convB = B.client.channel(`conv:${conv}`, { config: { private: true } });
  let typingSeen = false;
  convB.on("broadcast", { event: "typing" }, () => (typingSeen = true));
  try {
    await Promise.all([subscribed(convA), subscribed(convB)]);
    await convA.send({ type: "broadcast", event: "typing", payload: { user_id: A.id, stop: false } });
    for (let i = 0; i < 50 && !typingSeen; i++) await sleep(100);
    check("typing indicator reaches the other person", typingSeen);
  } catch (e) {
    check("typing indicator reaches the other person", false, e.message);
  }

  // presence (online indicator) respects privacy: B's "last seen" defaults to
  // contacts, so A may not see B online until B has chatted with A.
  try {
    const peek = A.client.channel(`presence:${B.id}`, { config: { private: true } });
    let denied = false;
    try {
      await subscribed(peek);
    } catch {
      denied = true;
    }
    await A.client.removeChannel(peek);
    check("online status stays hidden from a stranger", denied);
  } catch (e) {
    check("online status stays hidden from a stranger", false, e.message);
  }

  // B replies, which makes A one of B's contacts.
  const r1 = randomUUID();
  const { error: eR } = await B.client.rpc("send_message", {
    p_id: r1, p_conversation_id: conv, p_kind: "text", p_ciphertext: b64(40), p_nonce: b64(12), p_eph_key: b64(32),
    p_keys: keys, p_device_id: B.device,
  });
  check("reply", !eR, eR?.message);
  await expectEvent("sender gets the reply live", A, "message", (d) => d.id === r1);

  try {
    const own = B.client.channel(`presence:${B.id}`, { config: { private: true, presence: { key: "self" } } });
    await subscribed(own, () => own.track({ at: new Date().toISOString() }));
    const watch = A.client.channel(`presence:${B.id}`, { config: { private: true } });
    let online = false;
    watch.on("presence", { event: "sync" }, () => { online = Object.keys(watch.presenceState()).length > 0; });
    await subscribed(watch);
    for (let i = 0; i < 60 && !online; i++) await sleep(100);
    check("online status is visible live once they chat", online);
  } catch (e) {
    check("online status is visible live once they chat", false, e.message);
  }

  // receipts
  const now = new Date().toISOString();
  const { error: e3 } = await B.client.rpc("mark_delivered", { p_conversation_id: conv, p_up_to: now });
  const { error: e4 } = await B.client.rpc("mark_read", { p_conversation_id: conv, p_up_to: now });
  check("mark delivered / read", !e3 && !e4, (e3 ?? e4)?.message);
  await expectEvent("sender sees blue ticks live", A, "receipt", (d) => d.conversation_id === conv);

  // reactions (insert, then change — the app updates only the emoji column)
  const { error: e5 } = await B.client.from("message_reactions").insert({ message_id: m1, conversation_id: conv, user_id: B.id, emoji: "👍" });
  const { data: upd, error: e6 } = await B.client.from("message_reactions").update({ emoji: "❤️" }).eq("message_id", m1).eq("user_id", B.id).select("message_id");
  check("react and change reaction", !e5 && !e6 && upd?.length === 1, (e5 ?? e6)?.message);
  await expectEvent("reaction shows up live", A, "reaction", (d) => d.message_id === m1 && d.emoji === "❤️");

  // stars and pins
  const { error: e7 } = await B.client.from("message_stars").upsert(
    { user_id: B.id, message_id: m1, conversation_id: conv }, { onConflict: "user_id,message_id", ignoreDuplicates: true });
  const { error: e7b } = await B.client.from("message_stars").upsert(
    { user_id: B.id, message_id: m1, conversation_id: conv }, { onConflict: "user_id,message_id", ignoreDuplicates: true });
  check("star a message (twice)", !e7 && !e7b, (e7 ?? e7b)?.message);
  const { error: e8 } = await A.client.from("conversation_pins").insert({ conversation_id: conv, message_id: m1, pinned_by: A.id });
  check("pin a message", !e8, e8?.message);
  await expectEvent("pin shows up live", B, "pins", (d) => d.conversation_id === conv);

  // edit and delete for everyone
  const { error: e9 } = await A.client.rpc("edit_message", { p_id: m1, p_ciphertext: b64(40), p_nonce: b64(12), p_eph_key: b64(32), p_keys: keys });
  check("edit a message", !e9, e9?.message);
  await expectEvent("edit shows up live", B, "message", (d) => d.id === m1 && d.edited_at);

  // ---- statuses
  const { error: s1 } = await A.client.from("statuses").insert({ kind: "text", body: "E2E status", background: "#E2BC1F", font: 0 });
  check("post a text status", !s1, s1?.message);
  await expectEvent("contact sees the new status live", B, "status", (d) => d.user_id === A.id && d.op === "insert");
  const path = `${A.id}/${randomUUID()}.jpg`;
  const { error: s2 } = await A.client.storage.from("status").upload(path, JPEG, { contentType: "image/jpeg", upsert: false });
  const { error: s3 } = await A.client.from("statuses").insert({ kind: "image", media_path: path, caption: "E2E photo" });
  check("post a photo status (upload + row)", !s2 && !s3, (s2 ?? s3)?.message);
  const { data: feed, error: s4 } = await B.client.rpc("get_status_feed");
  const mine = (feed ?? []).find((r) => r.user_id === A.id);
  check("contact's status feed lists both", !s4 && mine?.statuses?.length === 2, s4?.message ?? `${mine?.statuses?.length ?? 0} items`);
  const photo = mine?.statuses?.find((s) => s.kind === "image");
  if (photo) {
    const { data: signed, error: s5 } = await B.client.storage.from("status").createSignedUrl(photo.media_path, 60);
    let fetched = false;
    if (signed?.signedUrl) fetched = (await fetch(signed.signedUrl)).ok;
    check("contact can open the photo", !s5 && fetched, s5?.message);
    const { error: s6 } = await B.client.rpc("mark_status_viewed", { p_status_id: photo.id });
    check("mark status viewed", !s6, s6?.message);
    await expectEvent("owner sees the view live", A, "status_view", (d) => d.status_id === photo.id);
    const { data: viewers } = await A.client.rpc("get_status_viewers", { p_status_id: photo.id });
    check("owner sees who viewed", viewers?.length === 1);
  }
  const { error: s7 } = await B.client.from("status_mutes").upsert({ muted_user_id: A.id }, { onConflict: "user_id,muted_user_id", ignoreDuplicates: true });
  check("mute someone's status", !s7, s7?.message);

  // ---- profile change
  const { error: p1 } = await A.client.from("profiles").update({ about: "Live about" }).eq("id", A.id);
  check("change about", !p1, p1?.message);
  await expectEvent("chat partner gets the profile change live", B, "profile", (d) => d.user_id === A.id);

  // ---- groups
  const { data: g, error: g1 } = await A.client.rpc("create_group", { p_name: "E2E group", p_description: "", p_member_ids: [B.id] });
  check("create a group", !g1 && g?.conversation_id, g1?.message);
  if (g?.conversation_id) {
    await expectEvent("new member sees the group live", B, "conversation", (d) => d.conversation_id === g.conversation_id);
    const m2 = randomUUID();
    const { error: g2 } = await A.client.rpc("send_message", {
      p_id: m2, p_conversation_id: g.conversation_id, p_kind: "text", p_ciphertext: b64(40), p_nonce: b64(12), p_eph_key: b64(32),
      p_keys: keys, p_device_id: A.device,
    });
    check("send a group message", !g2, g2?.message);
    await expectEvent("group member gets it live", B, "message", (d) => d.id === m2);
    const { error: g3 } = await A.client.rpc("update_group_info", { p_conversation_id: g.conversation_id, p_name: "E2E group renamed" });
    check("rename the group", !g3, g3?.message);
  }

  // ---- calls (signalling)
  const { data: call, error: c1 } = await A.client.rpc("start_call", { p_conversation_id: conv, p_media: "audio" });
  check("start a call", !c1 && call?.id, c1?.message);
  if (call?.id) {
    await expectEvent("callee rings live", B, "call", (d) => (d.id ?? d.call_id) === call.id);
    const { error: c2 } = await B.client.rpc("answer_call", { p_call_id: call.id });
    check("answer the call", !c2, c2?.message);
    await expectEvent("caller sees the answer live", A, "call", (d) => (d.id ?? d.call_id) === call.id && d.status === "active");
    const { error: c3 } = await A.client.rpc("end_call", { p_call_id: call.id, p_reason: "hangup" });
    check("end the call", !c3, c3?.message);
    const { data: ice, error: c4 } = await A.client.functions.invoke("ice-servers", { body: {} });
    check("STUN/TURN servers for calls", !c4 && Array.isArray(ice?.iceServers), c4 ? await fnError(c4) : `relay (TURN) available: ${ice?.relay === true}`);
  }

  // ---- delete for everyone
  const { error: d1 } = await A.client.rpc("delete_message_for_everyone", { p_id: m1 });
  check("delete for everyone", !d1, d1?.message);
  await expectEvent("deletion shows up live", B, "message", (d) => d.id === m1 && d.deleted_at);

}

try {
  await Promise.race([
    main(),
    sleep(240000).then(() => {
      throw new Error("timed out after 4 minutes");
    }),
  ]);
} catch (e) {
  check("run", false, e.message);
} finally {
  for (const u of created) {
    try {
      const { error } = await u.client.functions.invoke("delete-account", { body: { confirm: "DELETE" } });
      check(`delete test account ${u.tag}`, !error, error ? await fnError(error) : "");
    } catch (e) {
      check(`delete test account ${u.tag}`, false, e.message);
    }
  }
  console.log(`\n${results.length - failures} passed, ${failures} failed`);
  process.exit(failures ? 1 : 0);
}
