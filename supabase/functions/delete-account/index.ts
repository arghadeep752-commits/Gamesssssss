// Permanently deletes the caller's Hime account: their uploaded files, then
// the auth user, which cascades to every row they own. Group ownership is
// handed over automatically by database triggers.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { adminClient, corsHeaders, handleError, HttpError, json, jwtClaims, requireUser } from "../_shared/http.ts";

async function removeFolder(admin: ReturnType<typeof adminClient>, bucket: string, prefix: string) {
  const { data } = await admin.storage.from(bucket).list(prefix, { limit: 1000 });
  const paths = (data ?? []).filter((f) => f.id).map((f) => `${prefix}/${f.name}`);
  for (let i = 0; i < paths.length; i += 100) {
    await admin.storage.from(bucket).remove(paths.slice(i, i + 100));
  }
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
  try {
    const admin = adminClient();
    const { user, jwt } = await requireUser(req, admin);
    const input = await req.json().catch(() => ({}));
    if (input.confirm !== "DELETE") throw new HttpError(400, "confirmation_required");

    // Accounts protected by two-step verification must have passed it.
    const { data: factors } = await admin.auth.admin.mfa.listFactors({ userId: user.id });
    const hasVerifiedFactor = (factors?.factors ?? []).some((f) => f.status === "verified");
    if (hasVerifiedFactor && jwtClaims(jwt).aal !== "aal2") throw new HttpError(403, "mfa_required");

    // Encrypted chat media uploaded by this user.
    const { data: attachments } = await admin.from("attachments").select("path").eq("uploader_id", user.id);
    const mediaPaths = (attachments ?? []).map((a) => a.path as string);
    for (let i = 0; i < mediaPaths.length; i += 100) {
      await admin.storage.from("media").remove(mediaPaths.slice(i, i + 100));
    }
    await removeFolder(admin, "status", user.id);
    await removeFolder(admin, "avatars", `users/${user.id}`);

    const { error } = await admin.auth.admin.deleteUser(user.id);
    if (error) throw error;
    return json({ deleted: true });
  } catch (e) {
    return handleError(e);
  }
});
