const SLUG_PATTERN = /^[a-z0-9][a-z0-9-]{1,47}$/;

/** Turns "Shri Ram" into "shri-ram". Returns '' when nothing Latin remains (e.g. a Hindi-only name). */
export function slugify(input: string, maxLength = 48): string {
  return input
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, maxLength)
    .replace(/-+$/g, '');
}

/** Same pattern the Firestore rules enforce for category document ids. */
export function isValidSlug(value: string): boolean {
  return SLUG_PATTERN.test(value);
}

/** A slug for a name, with a short random suffix when the name has no Latin characters. */
export function slugForName(name: string, random: () => number = Math.random): string {
  const base = slugify(name, 40);
  if (isValidSlug(base)) return base;
  const suffix = Math.floor(random() * 36 ** 6)
    .toString(36)
    .padStart(6, '0');
  return base.length >= 1 ? `${base}-${suffix}` : `category-${suffix}`;
}
