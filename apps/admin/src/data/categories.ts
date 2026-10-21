import {
  collection,
  doc,
  getDoc,
  getDocs,
  onSnapshot,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
  updateDoc,
  writeBatch,
} from '@react-native-firebase/firestore';
import { putFile, ref } from '@react-native-firebase/storage';
import {
  CALLABLES,
  COLLECTIONS,
  categoryCoverUploadPath,
  toCategory,
  type Category,
  type ImageExtension,
} from '@devdarshan/shared';
import { AppError } from '../errors';
import { callFunction, db, storage } from '../firebase';

const categories = () => collection(db, COLLECTIONS.categories);

export async function fetchAllCategories(): Promise<Category[]> {
  const snap = await getDocs(query(categories(), orderBy('sortOrder', 'asc')));
  return snap.docs.map((d) => toCategory(d.id, d.data()));
}

export function watchCategory(id: string, onChange: (c: Category | null) => void, onError: (e: unknown) => void) {
  return onSnapshot(
    doc(db, COLLECTIONS.categories, id),
    (snap) => onChange(snap.exists() ? toCategory(snap.id, snap.data()) : null),
    onError,
  );
}

export interface CategoryInput {
  name: string;
  nameHi: string;
  description: string;
  isActive: boolean;
}

export async function createCategory(slug: string, input: CategoryInput, sortOrder: number, uid: string): Promise<void> {
  const target = doc(db, COLLECTIONS.categories, slug);
  const existing = await getDoc(target);
  if (existing.exists()) throw new AppError('E_EXISTS', `A category with the id "${slug}" already exists.`);
  await setDoc(target, {
    name: input.name || input.nameHi,
    nameHi: input.nameHi,
    slug,
    description: input.description,
    sortOrder,
    isActive: input.isActive,
    createdAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
    updatedBy: uid,
  });
}

export async function updateCategory(id: string, input: CategoryInput, uid: string): Promise<void> {
  await updateDoc(doc(db, COLLECTIONS.categories, id), {
    name: input.name || input.nameHi,
    nameHi: input.nameHi,
    description: input.description,
    isActive: input.isActive,
    updatedAt: serverTimestamp(),
    updatedBy: uid,
  });
}

export async function setCategoryActive(id: string, isActive: boolean, uid: string): Promise<void> {
  await updateDoc(doc(db, COLLECTIONS.categories, id), { isActive, updatedAt: serverTimestamp(), updatedBy: uid });
}

/** Swaps the display order of two categories atomically. */
export async function swapCategoryOrder(a: Category, b: Category, uid: string): Promise<void> {
  const batch = writeBatch(db);
  const orderA = a.sortOrder === b.sortOrder ? b.sortOrder + 1 : b.sortOrder;
  batch.update(doc(db, COLLECTIONS.categories, a.id), { sortOrder: orderA, updatedAt: serverTimestamp(), updatedBy: uid });
  batch.update(doc(db, COLLECTIONS.categories, b.id), { sortOrder: a.sortOrder, updatedAt: serverTimestamp(), updatedBy: uid });
  await batch.commit();
}

export function uploadCategoryCover(
  categoryId: string,
  localUri: string,
  ext: ImageExtension,
  contentType: string,
  onProgress: (fraction: number) => void,
): Promise<void> {
  const task = putFile(ref(storage, categoryCoverUploadPath(categoryId, ext)), localUri, { contentType });
  const unsubscribe = task.on('state_changed', (s) => {
    if (s.totalBytes > 0) onProgress(s.bytesTransferred / s.totalBytes);
  });
  return Promise.resolve(task).then(
    () => {
      if (typeof unsubscribe === 'function') unsubscribe();
    },
    (error: unknown) => {
      if (typeof unsubscribe === 'function') unsubscribe();
      throw error;
    },
  );
}

export function deleteCategory(categoryId: string, moveToCategoryId: string | null) {
  return callFunction<{ categoryId: string; moveToCategoryId: string | null }, { ok: boolean; moved: number }>(
    CALLABLES.deleteCategory,
    { categoryId, moveToCategoryId },
  );
}

export function seedStarterCategories() {
  return callFunction<Record<string, never>, { ok: boolean; created: number; existing: number }>(
    CALLABLES.seedStarterCategories,
    {},
  );
}
