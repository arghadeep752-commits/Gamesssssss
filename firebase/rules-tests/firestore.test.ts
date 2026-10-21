import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
  type RulesTestEnvironment,
} from '@firebase/rules-unit-testing';
import {
  Timestamp,
  arrayUnion,
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  query,
  serverTimestamp,
  setDoc,
  updateDoc,
  where,
} from 'firebase/firestore';
import { afterAll, beforeAll, beforeEach, describe, it } from 'vitest';

const rulesPath = fileURLToPath(new URL('../firestore.rules', import.meta.url));
let env: RulesTestEnvironment;

const now = () => Timestamp.now();
const baseWallpaper = {
  title: 'Shri Ram',
  description: '',
  categoryIds: ['shri-ram'],
  tags: ['ram'],
  requestedStatus: 'published',
  processingError: null,
  createdBy: 'admin1',
  updatedBy: 'admin1',
};

beforeAll(async () => {
  env = await initializeTestEnvironment({
    projectId: 'demo-devdarshan',
    firestore: { rules: readFileSync(rulesPath, 'utf8'), host: '127.0.0.1', port: 8080 },
  });
});

afterAll(async () => {
  await env?.cleanup();
});

beforeEach(async () => {
  await env.clearFirestore();
  await env.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.firestore();
    await setDoc(doc(db, 'adminRoles/admin1'), { email: 'admin@example.com', grantedBy: 'bootstrap' });
    await setDoc(doc(db, 'adminRoles/roleonly'), { email: 'roleonly@example.com', grantedBy: 'admin1' });
    await setDoc(doc(db, 'wallpapers/pub1'), {
      ...baseWallpaper,
      status: 'published',
      processing: 'ready',
      thumbnailUrl: 'https://example.com/t.webp',
      favoriteCount: 0,
      createdAt: now(),
      updatedAt: now(),
    });
    await setDoc(doc(db, 'wallpapers/draft1'), {
      ...baseWallpaper,
      status: 'draft',
      processing: 'uploading',
      createdAt: now(),
      updatedAt: now(),
    });
    await setDoc(doc(db, 'wallpapers/ready1'), {
      ...baseWallpaper,
      status: 'draft',
      requestedStatus: 'draft',
      processing: 'ready',
      createdAt: now(),
      updatedAt: now(),
    });
    await setDoc(doc(db, 'categories/shri-ram'), {
      name: 'Shri Ram',
      nameHi: 'श्री राम',
      slug: 'shri-ram',
      description: '',
      sortOrder: 10,
      isActive: true,
      createdAt: now(),
      updatedAt: now(),
      updatedBy: 'admin1',
    });
    await setDoc(doc(db, 'categories/hidden'), {
      name: 'Hidden',
      nameHi: '',
      slug: 'hidden',
      description: '',
      sortOrder: 20,
      isActive: false,
      createdAt: now(),
      updatedAt: now(),
      updatedBy: 'admin1',
    });
    await setDoc(doc(db, 'appConfig/public'), { featuredWallpaperIds: [], updatedAt: now(), updatedBy: 'admin1' });
    await setDoc(doc(db, 'adminLog/e1'), { action: 'wallpaper.created' });
    await setDoc(doc(db, 'users/user2/favorites/pub1'), { wallpaperId: 'pub1', createdAt: now() });
  });
});

const guest = () => env.unauthenticatedContext().firestore();
const user = () => env.authenticatedContext('user1', { email: 'user@example.com' }).firestore();
const admin = () => env.authenticatedContext('admin1', { admin: true, email: 'admin@example.com' }).firestore();
/** Has the claim but no role document (e.g. revoked): must be treated as a normal user. */
const revokedAdmin = () => env.authenticatedContext('mallory', { admin: true }).firestore();
/** Has a role document but no claim (claim removed or never set): also a normal user. */
const roleOnly = () => env.authenticatedContext('roleonly', { email: 'roleonly@example.com' }).firestore();

const newDraft = () => ({
  ...baseWallpaper,
  status: 'draft',
  processing: 'uploading',
  createdAt: serverTimestamp(),
  updatedAt: serverTimestamp(),
});

describe('public reads', () => {
  it('lets anyone read published wallpapers but not drafts', async () => {
    await assertSucceeds(getDoc(doc(guest(), 'wallpapers/pub1')));
    await assertFails(getDoc(doc(guest(), 'wallpapers/draft1')));
  });

  it('only allows wallpaper queries constrained to published', async () => {
    await assertSucceeds(getDocs(query(collection(guest(), 'wallpapers'), where('status', '==', 'published'))));
    await assertFails(getDocs(collection(guest(), 'wallpapers')));
  });

  it('hides inactive categories from the public', async () => {
    await assertSucceeds(getDoc(doc(guest(), 'categories/shri-ram')));
    await assertFails(getDoc(doc(guest(), 'categories/hidden')));
    await assertSucceeds(getDoc(doc(admin(), 'categories/hidden')));
  });

  it('serves the public config read-only', async () => {
    await assertSucceeds(getDoc(doc(guest(), 'appConfig/public')));
    await assertFails(setDoc(doc(user(), 'appConfig/public'), { maintenanceMode: true }));
  });
});

describe('wallpaper writes', () => {
  it('blocks non-admins and revoked admins', async () => {
    await assertFails(setDoc(doc(user(), 'wallpapers/w1'), { ...newDraft(), createdBy: 'user1', updatedBy: 'user1' }));
    await assertFails(setDoc(doc(revokedAdmin(), 'wallpapers/w1'), { ...newDraft(), createdBy: 'mallory', updatedBy: 'mallory' }));
    await assertFails(setDoc(doc(roleOnly(), 'wallpapers/w1'), { ...newDraft(), createdBy: 'roleonly', updatedBy: 'roleonly' }));
    await assertFails(getDoc(doc(roleOnly(), 'wallpapers/draft1')));
  });

  it('lets an admin create a valid draft', async () => {
    await assertSucceeds(setDoc(doc(admin(), 'wallpapers/w1'), newDraft()));
  });

  it('rejects creating an already-published wallpaper or setting server fields', async () => {
    await assertFails(setDoc(doc(admin(), 'wallpapers/w2'), { ...newDraft(), status: 'published' }));
    await assertFails(setDoc(doc(admin(), 'wallpapers/w3'), { ...newDraft(), thumbnailUrl: 'https://evil.example/x.jpg' }));
    await assertFails(setDoc(doc(admin(), 'wallpapers/w4'), { ...newDraft(), favoriteCount: 9999 }));
    await assertFails(setDoc(doc(admin(), 'wallpapers/w5'), { ...newDraft(), featured: true }));
  });

  it('validates editorial fields', async () => {
    await assertFails(setDoc(doc(admin(), 'wallpapers/w6'), { ...newDraft(), title: 'x' }));
    await assertFails(setDoc(doc(admin(), 'wallpapers/w7'), { ...newDraft(), categoryIds: [] }));
    await assertFails(setDoc(doc(admin(), 'wallpapers/w8'), { ...newDraft(), tags: new Array(16).fill('t') }));
  });

  it('only publishes processed images', async () => {
    await assertFails(
      updateDoc(doc(admin(), 'wallpapers/draft1'), { status: 'published', updatedAt: serverTimestamp(), updatedBy: 'admin1' }),
    );
    await assertSucceeds(
      updateDoc(doc(admin(), 'wallpapers/ready1'), {
        status: 'published',
        requestedStatus: 'published',
        updatedAt: serverTimestamp(),
        updatedBy: 'admin1',
      }),
    );
  });

  it('allows starting an image replacement but not faking processing results', async () => {
    await assertSucceeds(
      updateDoc(doc(admin(), 'wallpapers/pub1'), {
        processing: 'uploading',
        processingError: null,
        updatedAt: serverTimestamp(),
        updatedBy: 'admin1',
      }),
    );
    await assertFails(
      updateDoc(doc(admin(), 'wallpapers/draft1'), { processing: 'ready', updatedAt: serverTimestamp(), updatedBy: 'admin1' }),
    );
  });

  it('requires a fresh audit stamp', async () => {
    await assertFails(updateDoc(doc(admin(), 'wallpapers/pub1'), { title: 'Jai Shri Ram' }));
    await assertFails(
      updateDoc(doc(admin(), 'wallpapers/pub1'), { title: 'Jai Shri Ram', updatedAt: serverTimestamp(), updatedBy: 'someone-else' }),
    );
    await assertSucceeds(
      updateDoc(doc(admin(), 'wallpapers/pub1'), { title: 'Jai Shri Ram', updatedAt: serverTimestamp(), updatedBy: 'admin1' }),
    );
  });

  it('never allows direct deletes', async () => {
    await assertFails(deleteDoc(doc(admin(), 'wallpapers/pub1')));
  });
});

describe('categories', () => {
  const category = {
    name: 'Maa Durga',
    nameHi: 'माँ दुर्गा',
    slug: 'maa-durga',
    description: '',
    sortOrder: 30,
    isActive: true,
    createdAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
    updatedBy: 'admin1',
  };

  it('lets admins create categories with a matching slug id', async () => {
    await assertSucceeds(setDoc(doc(admin(), 'categories/maa-durga'), category));
    await assertFails(setDoc(doc(admin(), 'categories/Bad Slug'), { ...category, slug: 'Bad Slug' }));
    await assertFails(setDoc(doc(admin(), 'categories/other'), category));
    await assertFails(setDoc(doc(user(), 'categories/maa-durga'), { ...category, updatedBy: 'user1' }));
  });

  it('keeps the wallpaper count server-owned', async () => {
    await assertFails(
      updateDoc(doc(admin(), 'categories/shri-ram'), { wallpaperCount: 99, updatedAt: serverTimestamp(), updatedBy: 'admin1' }),
    );
    await assertSucceeds(
      updateDoc(doc(admin(), 'categories/shri-ram'), { isActive: false, updatedAt: serverTimestamp(), updatedBy: 'admin1' }),
    );
    await assertFails(deleteDoc(doc(admin(), 'categories/shri-ram')));
  });
});

describe('app config', () => {
  it('validates admin updates', async () => {
    await assertSucceeds(
      setDoc(
        doc(admin(), 'appConfig/public'),
        { featuredWallpaperIds: arrayUnion('pub1'), updatedAt: serverTimestamp(), updatedBy: 'admin1' },
        { merge: true },
      ),
    );
    await assertFails(
      setDoc(
        doc(admin(), 'appConfig/public'),
        { featuredWallpaperIds: Array.from({ length: 31 }, (_, i) => `w${i}`), updatedAt: serverTimestamp(), updatedBy: 'admin1' },
        { merge: true },
      ),
    );
    await assertFails(
      setDoc(doc(admin(), 'appConfig/public'), { unknownKey: 1, updatedAt: serverTimestamp(), updatedBy: 'admin1' }, { merge: true }),
    );
  });
});

describe('favourites', () => {
  const fav = (id: string) => ({ wallpaperId: id, createdAt: serverTimestamp() });

  it('lets users favourite published wallpapers only, for themselves only', async () => {
    await assertSucceeds(setDoc(doc(user(), 'users/user1/favorites/pub1'), fav('pub1')));
    await assertFails(setDoc(doc(user(), 'users/user1/favorites/draft1'), fav('draft1')));
    await assertFails(setDoc(doc(user(), 'users/user2/favorites/pub1'), fav('pub1')));
    await assertFails(setDoc(doc(guest(), 'users/user1/favorites/pub1'), fav('pub1')));
  });

  it('rejects malformed favourite documents', async () => {
    await assertFails(setDoc(doc(user(), 'users/user1/favorites/pub1'), { ...fav('pub1'), extra: true }));
    await assertFails(setDoc(doc(user(), 'users/user1/favorites/pub1'), fav('other')));
  });

  it("keeps each user's favourites private", async () => {
    await assertSucceeds(getDocs(collection(user(), 'users/user1/favorites')));
    await assertFails(getDocs(collection(user(), 'users/user2/favorites')));
    await assertFails(deleteDoc(doc(user(), 'users/user2/favorites/pub1')));
    await assertFails(getDocs(collection(admin(), 'users/user2/favorites')));
    await assertFails(getDoc(doc(admin(), 'users/user2/favorites/pub1')));
  });
});

describe('admin data', () => {
  it('never lets clients write roles, even admins', async () => {
    await assertFails(setDoc(doc(user(), 'adminRoles/user1'), { email: 'user@example.com' }));
    await assertFails(setDoc(doc(admin(), 'adminRoles/user1'), { email: 'user@example.com' }));
  });

  it('restricts the activity log and stats to admins', async () => {
    await assertFails(getDoc(doc(user(), 'adminLog/e1')));
    await assertSucceeds(getDoc(doc(admin(), 'adminLog/e1')));
    await assertFails(getDoc(doc(user(), 'stats/global')));
  });
});
