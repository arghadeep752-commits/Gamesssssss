// Scheduled housekeeping (called hourly by pg_cron with a shared secret):
//  * removes storage files queued by database triggers (deleted messages,
//    expired statuses, replaced avatars, deleted groups and accounts)
//  * deletes expired statuses (24 hours)
//  * prunes rows that only pointed at deleted messages
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { adminClient, corsHeaders, json } from "../_shared/http.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
  const admin = adminClient();
  const provided = req.headers.get("x-hime-cron") ?? "";
  const { data: secret } = await admin.from("app_secrets").select("value").eq("key", "cron_key").maybeSingle();
  if (!secret?.value || provided !== secret.value) return json({ error: "forbidden" }, 403);

  const report: Record<string, number> = { files: 0, statuses: 0, attachments: 0, failures: 0 };

  // 1. Expired statuses (their media is queued by a trigger on delete).
  const { data: expired } = await admin.from("statuses").delete().lt("expires_at", new Date().toISOString()).select("id");
  report.statuses = expired?.length ?? 0;

  // 2. Drain the storage deletion queue.
  for (let round = 0; round < 10; round++) {
    const { data: batch } = await admin.from("storage_cleanup_queue")
      .select("id, bucket, path, attempts").lt("attempts", 5).order("id").limit(100);
    if (!batch || batch.length === 0) break;
    const byBucket = new Map<string, { id: number; path: string }[]>();
    for (const row of batch) {
      const list = byBucket.get(row.bucket) ?? [];
      list.push({ id: row.id, path: row.path });
      byBucket.set(row.bucket, list);
    }
    for (const [bucket, rows] of byBucket) {
      const { error } = await admin.storage.from(bucket).remove(rows.map((r) => r.path));
      const ids = rows.map((r) => r.id);
      if (error) {
        report.failures += rows.length;
        for (const row of batch.filter((b) => ids.includes(b.id))) {
          await admin.from("storage_cleanup_queue").update({ attempts: row.attempts + 1 }).eq("id", row.id);
        }
      } else {
        report.files += rows.length;
        await admin.from("storage_cleanup_queue").delete().in("id", ids);
      }
    }
  }

  // 3. Attachment rows whose blobs were removed.
  const { data: gone } = await admin.from("attachments").delete()
    .not("deleted_at", "is", null).lt("deleted_at", new Date(Date.now() - 60 * 60 * 1000).toISOString()).select("id");
  report.attachments = gone?.length ?? 0;

  return json(report);
});
