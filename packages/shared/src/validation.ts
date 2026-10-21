import { z } from 'zod';
import { LIMITS } from './constants';

/**
 * Validation shared by the admin app (forms) and the Cloud Functions (callable
 * inputs). The Firestore rules enforce the same limits independently, so a
 * modified client still cannot write invalid data.
 */

const firestoreId = z
  .string()
  .trim()
  .min(1, 'Missing id')
  .max(LIMITS.idMaxLength, 'Invalid id')
  .regex(/^[A-Za-z0-9_-]+$/, 'Invalid id');

export const categorySlugSchema = z
  .string()
  .trim()
  .regex(/^[a-z0-9][a-z0-9-]{1,47}$/, 'Use 2–48 lowercase letters, numbers or hyphens');

/** Splits "ram, Sita ,  #ayodhya" into ["ram", "Sita", "ayodhya"], de-duplicated case-insensitively. */
export function parseTags(input: string): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of input.split(/[,\n#]+/)) {
    const tag = raw.trim().replace(/\s+/g, ' ').slice(0, LIMITS.tagMaxLength);
    const key = tag.toLowerCase();
    if (!tag || seen.has(key)) continue;
    seen.add(key);
    result.push(tag);
  }
  return result;
}

export const wallpaperFormSchema = z.object({
  title: z
    .string()
    .trim()
    .min(LIMITS.titleMin, `Title needs at least ${LIMITS.titleMin} characters`)
    .max(LIMITS.titleMax, `Keep the title under ${LIMITS.titleMax} characters`),
  description: z.string().trim().max(LIMITS.descriptionMax, `Keep the description under ${LIMITS.descriptionMax} characters`),
  categoryIds: z
    .array(z.string().min(1))
    .min(LIMITS.categoriesPerWallpaperMin, 'Choose at least one category')
    .max(LIMITS.categoriesPerWallpaperMax, `Choose at most ${LIMITS.categoriesPerWallpaperMax} categories`),
  tagsText: z.string().refine((value) => parseTags(value).length <= LIMITS.tagsMax, {
    message: `Use at most ${LIMITS.tagsMax} tags`,
  }),
  featured: z.boolean(),
  requestedStatus: z.enum(['draft', 'published']),
});

export type WallpaperFormValues = z.infer<typeof wallpaperFormSchema>;

export const categoryFormSchema = z
  .object({
    name: z.string().trim().max(LIMITS.categoryNameMax, `Keep the name under ${LIMITS.categoryNameMax} characters`),
    nameHi: z.string().trim().max(LIMITS.categoryNameMax, `Keep the name under ${LIMITS.categoryNameMax} characters`),
    description: z
      .string()
      .trim()
      .max(LIMITS.categoryDescriptionMax, `Keep the description under ${LIMITS.categoryDescriptionMax} characters`),
    isActive: z.boolean(),
  })
  .refine((v) => v.name.length > 0 || v.nameHi.length > 0, {
    message: 'Enter a name in English or Hindi',
    path: ['name'],
  });

export type CategoryFormValues = z.infer<typeof categoryFormSchema>;

/* ---------- Callable function inputs ---------- */

export const deleteWallpaperInput = z.object({ wallpaperId: firestoreId });
export const retryProcessingInput = z.object({ wallpaperId: firestoreId });
export const recordDownloadInput = z.object({ wallpaperId: firestoreId });

export const deleteCategoryInput = z.object({
  categoryId: categorySlugSchema,
  moveToCategoryId: categorySlugSchema.nullish(),
});

export const setAdminRoleInput = z.object({
  email: z.string().trim().toLowerCase().email('Enter a valid email address'),
  grant: z.boolean(),
});

export type DeleteCategoryInput = z.infer<typeof deleteCategoryInput>;
export type SetAdminRoleInput = z.infer<typeof setAdminRoleInput>;

/** Returns the first validation message, for showing a single error line. */
export function firstIssue(error: z.ZodError): string {
  return error.issues[0]?.message ?? 'Invalid input';
}
