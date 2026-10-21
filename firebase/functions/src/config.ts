import { createHash, timingSafeEqual } from 'node:crypto';
import { FUNCTIONS_REGION } from './shared/constants';

/**
 * Deployment settings come from functions/.env (loaded by the Firebase CLI at
 * deploy time and by the runtime). They are not secrets.
 */

/** Firestore-triggered functions must live in the database's region. */
export const FIRESTORE_REGION = process.env.DEVDARSHAN_FIRESTORE_REGION || 'asia-south1';

/** Storage-triggered functions must live in the bucket's region. */
export const STORAGE_REGION = process.env.DEVDARSHAN_STORAGE_REGION || 'us-central1';

/** Callable functions run close to the users (Mumbai); the apps call this region. */
export const CALLABLE_REGION = FUNCTIONS_REGION;

export const ENFORCE_APP_CHECK = (process.env.DEVDARSHAN_ENFORCE_APP_CHECK || 'false').toLowerCase() === 'true';

function sha256Hex(value: string): string {
  return createHash('sha256').update(value, 'utf8').digest('hex');
}

/** True when a bootstrap admin is configured (plain email or its SHA-256). */
export function hasBootstrapAdmin(): boolean {
  return Boolean(process.env.DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL_SHA256?.trim() || process.env.DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL?.trim());
}

/**
 * Whether `email` is the configured first admin. The setting is normally the
 * SHA-256 of the lower-case address (DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL_SHA256), so the
 * address itself never appears in the public repository.
 */
export function isBootstrapAdminEmail(email: string | null | undefined): boolean {
  const normalised = (email ?? '').trim().toLowerCase();
  if (!normalised) return false;
  const expectedHash = (process.env.DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL_SHA256 || '').trim().toLowerCase();
  if (expectedHash) {
    const actual = Buffer.from(sha256Hex(normalised), 'utf8');
    const expected = Buffer.from(expectedHash, 'utf8');
    return actual.length === expected.length && timingSafeEqual(actual, expected);
  }
  const plain = (process.env.DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL || '').trim().toLowerCase();
  return plain.length > 0 && plain === normalised;
}
