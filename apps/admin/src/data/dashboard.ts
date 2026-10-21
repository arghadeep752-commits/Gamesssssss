import {
  Timestamp,
  collection,
  doc,
  getCountFromServer,
  getDoc,
  getDocs,
  limit,
  orderBy,
  query,
  where,
} from '@react-native-firebase/firestore';
import {
  COLLECTIONS,
  STATS_DOC_ID,
  toAdminLogEntry,
  toGlobalStats,
  toWallpaper,
  type AdminLogEntry,
  type GlobalStats,
  type Wallpaper,
} from '@devdarshan/shared';
import { db } from '../firebase';

export interface DashboardData {
  published: number;
  drafts: number;
  needsAttention: number;
  total: number;
  categories: number;
  activeCategories: number;
  uploadsThisWeek: number;
  stats: GlobalStats;
  recent: Wallpaper[];
  activity: AdminLogEntry[];
}

/** Every number here comes from the backend (aggregation queries or server-kept stats). */
export async function fetchDashboard(): Promise<DashboardData> {
  const wallpapers = collection(db, COLLECTIONS.wallpapers);
  const categories = collection(db, COLLECTIONS.categories);
  const weekAgo = Timestamp.fromMillis(Date.now() - 7 * 24 * 60 * 60 * 1000);
  const count = async (q: Parameters<typeof getCountFromServer>[0]) => (await getCountFromServer(q)).data().count;

  const [published, drafts, needsAttention, total, categoryCount, activeCategories, uploadsThisWeek, statsSnap, recentSnap, logSnap] =
    await Promise.all([
      count(query(wallpapers, where('status', '==', 'published'))),
      count(query(wallpapers, where('status', '==', 'draft'))),
      count(query(wallpapers, where('processing', 'in', ['uploading', 'processing', 'failed']))),
      count(wallpapers),
      count(categories),
      count(query(categories, where('isActive', '==', true))),
      count(query(wallpapers, where('processing', '==', 'ready'), where('createdAt', '>=', weekAgo))),
      getDoc(doc(db, COLLECTIONS.stats, STATS_DOC_ID)),
      getDocs(query(wallpapers, orderBy('createdAt', 'desc'), limit(5))),
      getDocs(query(collection(db, COLLECTIONS.adminLog), orderBy('createdAt', 'desc'), limit(8))),
    ]);

  return {
    published,
    drafts,
    needsAttention,
    total,
    categories: categoryCount,
    activeCategories,
    uploadsThisWeek,
    stats: toGlobalStats(statsSnap.exists() ? statsSnap.data() : null),
    recent: recentSnap.docs.map((d) => toWallpaper(d.id, d.data())),
    activity: logSnap.docs.map((d) => toAdminLogEntry(d.id, d.data())),
  };
}

export async function fetchActivity(pageSize = 50): Promise<AdminLogEntry[]> {
  const snap = await getDocs(query(collection(db, COLLECTIONS.adminLog), orderBy('createdAt', 'desc'), limit(pageSize)));
  return snap.docs.map((d) => toAdminLogEntry(d.id, d.data()));
}
