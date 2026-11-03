// Returns STUN/TURN servers for WebRTC calls. TURN relays are needed when
// both phones sit behind carrier-grade NAT (very common on mobile data).
//
// Configure ONE of these provider secrets (Supabase dashboard → Edge
// Functions → Secrets):
//   Cloudflare Realtime TURN:  CLOUDFLARE_TURN_KEY_ID + CLOUDFLARE_TURN_API_TOKEN
//   Metered.ca TURN:           METERED_TURN_APP + METERED_TURN_API_KEY
//   Any TURN server (coturn):  TURN_URLS (comma separated) + TURN_USERNAME + TURN_CREDENTIAL
// Without them calls still work on most Wi-Fi networks via STUN only.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { adminClient, corsHeaders, handleError, json, requireUser } from "../_shared/http.ts";

type IceServer = { urls: string | string[]; username?: string; credential?: string };

const STUN: IceServer[] = [
  { urls: ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"] },
  { urls: "stun:stun.cloudflare.com:3478" },
];

function normalize(input: unknown): IceServer[] {
  const list = Array.isArray(input) ? input : input ? [input] : [];
  return list
    .filter((s): s is Record<string, unknown> => !!s && typeof s === "object" && "urls" in s)
    .map((s) => ({
      urls: s.urls as string | string[],
      ...(typeof s.username === "string" ? { username: s.username } : {}),
      ...(typeof s.credential === "string" ? { credential: s.credential } : {}),
    }));
}

async function relayServers(): Promise<IceServer[]> {
  const cfKey = Deno.env.get("CLOUDFLARE_TURN_KEY_ID");
  const cfToken = Deno.env.get("CLOUDFLARE_TURN_API_TOKEN");
  if (cfKey && cfToken) {
    const res = await fetch(
      `https://rtc.live.cloudflare.com/v1/turn/keys/${cfKey}/credentials/generate-ice-servers`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${cfToken}`, "Content-Type": "application/json" },
        body: JSON.stringify({ ttl: 86400 }),
      },
    );
    if (!res.ok) throw new Error(`cloudflare_turn_${res.status}`);
    const body = await res.json();
    return normalize(body.iceServers);
  }
  const meteredApp = Deno.env.get("METERED_TURN_APP");
  const meteredKey = Deno.env.get("METERED_TURN_API_KEY");
  if (meteredApp && meteredKey) {
    const res = await fetch(
      `https://${meteredApp}.metered.live/api/v1/turn/credentials?apiKey=${encodeURIComponent(meteredKey)}`,
    );
    if (!res.ok) throw new Error(`metered_turn_${res.status}`);
    return normalize(await res.json());
  }
  const urls = Deno.env.get("TURN_URLS");
  if (urls) {
    return [{
      urls: urls.split(",").map((u) => u.trim()).filter(Boolean),
      username: Deno.env.get("TURN_USERNAME") ?? undefined,
      credential: Deno.env.get("TURN_CREDENTIAL") ?? undefined,
    }];
  }
  return [];
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
  try {
    await requireUser(req, adminClient());
    let relay: IceServer[] = [];
    let relayError: string | null = null;
    try {
      relay = await relayServers();
    } catch (e) {
      relayError = e instanceof Error ? e.message : String(e);
      console.error("TURN provider error", relayError);
    }
    return json({
      iceServers: [...STUN, ...relay],
      relay: relay.length > 0,
      relayError,
      ttl: 3600,
    });
  } catch (e) {
    return handleError(e);
  }
});
