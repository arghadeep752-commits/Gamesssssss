import { getApps, initializeApp } from 'firebase-admin/app';
import { getAuth } from 'firebase-admin/auth';
import { getFirestore } from 'firebase-admin/firestore';
import { getStorage } from 'firebase-admin/storage';

if (getApps().length === 0) initializeApp();

export const db = () => getFirestore();
export const bucket = () => getStorage().bucket();
export const adminAuth = () => getAuth();

/** gRPC NOT_FOUND, as thrown by update() on a missing document. */
export function isNotFound(error: unknown): boolean {
  return typeof error === 'object' && error !== null && 'code' in error && (error as { code: unknown }).code === 5;
}
