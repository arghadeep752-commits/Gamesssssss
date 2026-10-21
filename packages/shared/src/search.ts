import { LIMITS } from './constants';

/**
 * Firestore has no full-text search, so every wallpaper stores a server-generated
 * `searchKeywords` array (prefixes of every word in its title, tags and category
 * names). A query looks up ONE term with `array-contains` and the remaining terms
 * are matched on the device against the same array.
 *
 * Latin words are also folded so common transliteration variants meet:
 * "Shree"/"Shri", "Raam"/"Ram", "Shiv"/"Shiva", "Ganesh"/"Ganesha".
 */

const LATIN_DIACRITICS = /[̀-ͯ]/g;
const NOT_WORD = /[^\p{L}\p{M}\p{N}\s]/gu;
const LATIN_ONLY = /^[a-z0-9]+$/;

export function normalizeText(input: string): string {
  return input
    .normalize('NFKD')
    .replace(LATIN_DIACRITICS, '')
    .normalize('NFC')
    .toLowerCase()
    .replace(/[-_/.,|]+/g, ' ')
    .replace(NOT_WORD, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function tokenize(input: string): string[] {
  const normalized = normalizeText(input);
  return normalized ? normalized.split(' ') : [];
}

function codePoints(s: string): string[] {
  return Array.from(s);
}

/** Folds common Hindi transliteration variants of a Latin word. */
export function foldLatin(token: string): string {
  if (!LATIN_ONLY.test(token)) return token;
  return token
    .replace(/aa+/g, 'a')
    .replace(/(ee|ii)+/g, 'i')
    .replace(/(oo|uu)+/g, 'u')
    .replace(/w/g, 'v')
    .replace(/ph/g, 'f');
}

/**
 * "ganesha" -> "ganesh", "rama" -> "ram": drops the trailing inherent vowel that
 * transliterated Hindi spells inconsistently. Applied to documents and queries
 * alike, so "Shiv"/"Shiva" and "Ganesh"/"Ganesha" always meet.
 */
export function stemLatin(token: string): string {
  if (!LATIN_ONLY.test(token) || token.length < 4 || !token.endsWith('a')) return token;
  return token.slice(0, -1);
}

function addPrefixes(target: Set<string>, token: string): void {
  const chars = codePoints(token);
  if (chars.length < 2) return;
  const max = Math.min(chars.length, LIMITS.searchTokenPrefixMax);
  for (let i = 2; i <= max; i += 1) target.add(chars.slice(0, i).join(''));
  if (chars.length <= 30) target.add(token);
}

export interface SearchSource {
  title?: string;
  tags?: readonly string[];
  /** Extra phrases such as category names in English and Hindi. */
  extra?: readonly string[];
}

export function buildSearchKeywords(source: SearchSource): string[] {
  const keywords = new Set<string>();
  const phrases = [source.title ?? '', ...(source.tags ?? []), ...(source.extra ?? [])];
  for (const phrase of phrases) {
    for (const token of tokenize(phrase)) {
      const folded = foldLatin(token);
      addPrefixes(keywords, token);
      if (folded !== token) addPrefixes(keywords, folded);
      const stem = stemLatin(folded);
      if (stem !== folded) addPrefixes(keywords, stem);
    }
  }
  // Shortest entries first so the cap never drops the prefixes people type first.
  return [...keywords]
    .sort((a, b) => codePoints(a).length - codePoints(b).length || a.localeCompare(b))
    .slice(0, LIMITS.searchKeywordsMax);
}

export interface SearchQuery {
  /** The single term sent to Firestore with `array-contains`, or null when the input is too short. */
  term: string | null;
  /** Every term; results must contain all of them. */
  terms: string[];
}

export function parseSearchQuery(input: string): SearchQuery {
  const terms = tokenize(input.slice(0, LIMITS.searchQueryMaxLength))
    .map((t) => stemLatin(foldLatin(t)))
    .filter((t) => codePoints(t).length >= 2)
    .map((t) => codePoints(t).slice(0, LIMITS.searchTokenPrefixMax).join(''));
  const unique = [...new Set(terms)];
  if (unique.length === 0) return { term: null, terms: [] };
  // The longest term is the most selective one to send to the server.
  const term = [...unique].sort((a, b) => codePoints(b).length - codePoints(a).length)[0] ?? null;
  return { term, terms: unique };
}

export function matchesAllTerms(keywords: readonly string[] | undefined, terms: readonly string[]): boolean {
  if (terms.length === 0) return true;
  const set = new Set(keywords ?? []);
  return terms.every((t) => set.has(t));
}
