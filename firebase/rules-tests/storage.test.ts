import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
  type RulesTestEnvironment,
} from '@firebase/rules-unit-testing';
import { doc, setDoc } from 'firebase/firestore';
import { getBytes, ref, uploadBytes } from 'firebase/storage';
import { afterAll, beforeAll, beforeEach, describe, it } from 'vitest';

let env: RulesTestEnvironment;
const bytes = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3, 4]);

beforeAll(async () => {
  env = await initializeTestEnvironment({
    projectId: 'demo-devdarshan',
    firestore: {
      rules: readFileSync(fileURLToPath(new URL('../firestore.rules', import.meta.url)), 'utf8'),
      host: '127.0.0.1',
      port: 8080,
    },
    storage: {
      rules: readFileSync(fileURLToPath(new URL('../storage.rules', import.meta.url)), 'utf8'),
      host: '127.0.0.1',
      port: 9199,
    },
  });
});

afterAll(async () => {
  await env?.cleanup();
});

beforeEach(async () => {
  await env.clearFirestore();
  await env.clearStorage();
  await env.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.firestore();
    await setDoc(doc(db, 'adminRoles/admin1'), { email: 'admin@example.com' });
    await setDoc(doc(db, 'wallpapers/pub1'), { status: 'published' });
    await setDoc(doc(db, 'wallpapers/draft1'), { status: 'draft' });
    const storage = ctx.storage();
    await uploadBytes(ref(storage, 'wallpapers/pub1/thumb.webp'), bytes, { contentType: 'image/webp' });
    await uploadBytes(ref(storage, 'wallpapers/draft1/thumb.webp'), bytes, { contentType: 'image/webp' });
  });
});

const adminStorage = () => env.authenticatedContext('admin1', { admin: true }).storage();
const userStorage = () => env.authenticatedContext('user1').storage();
const guestStorage = () => env.unauthenticatedContext().storage();

describe('uploads', () => {
  it('accepts admin JPEG/PNG/WebP sources at the expected path', async () => {
    await assertSucceeds(uploadBytes(ref(adminStorage(), 'uploads/wallpapers/w1/source.jpg'), bytes, { contentType: 'image/jpeg' }));
    await assertSucceeds(uploadBytes(ref(adminStorage(), 'uploads/categories/shri-ram/cover.png'), bytes, { contentType: 'image/png' }));
  });

  it('rejects non-admins, other file names and other types', async () => {
    await assertFails(uploadBytes(ref(userStorage(), 'uploads/wallpapers/w1/source.jpg'), bytes, { contentType: 'image/jpeg' }));
    await assertFails(uploadBytes(ref(adminStorage(), 'uploads/wallpapers/w1/evil.jpg'), bytes, { contentType: 'image/jpeg' }));
    await assertFails(uploadBytes(ref(adminStorage(), 'uploads/wallpapers/w1/source.jpg'), bytes, { contentType: 'text/html' }));
    await assertFails(uploadBytes(ref(adminStorage(), 'wallpapers/w1/preview.webp'), bytes, { contentType: 'image/webp' }));
  });
});

describe('processed files', () => {
  it('are readable when the wallpaper is published', async () => {
    await assertSucceeds(getBytes(ref(guestStorage(), 'wallpapers/pub1/thumb.webp')));
  });

  it('stay private while the wallpaper is a draft', async () => {
    await assertFails(getBytes(ref(guestStorage(), 'wallpapers/draft1/thumb.webp')));
    await assertSucceeds(getBytes(ref(adminStorage(), 'wallpapers/draft1/thumb.webp')));
  });
});
