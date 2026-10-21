import { describe, expect, it } from 'vitest';
import {
  buildSearchKeywords,
  foldLatin,
  matchesAllTerms,
  normalizeText,
  parseSearchQuery,
  stemLatin,
  tokenize,
} from '../src/search';

describe('normalizeText', () => {
  it('lowercases, strips punctuation and Latin accents', () => {
    expect(normalizeText('  Shrī  Rām — Darbār!! ')).toBe('shri ram darbar');
  });

  it('keeps Devanagari vowel signs intact', () => {
    expect(normalizeText('श्री कृष्ण')).toBe('श्री कृष्ण');
  });

  it('splits on hyphens and slashes', () => {
    expect(tokenize('radha-krishna/vrindavan')).toEqual(['radha', 'krishna', 'vrindavan']);
  });
});

describe('foldLatin', () => {
  it('folds common transliteration variants', () => {
    expect(foldLatin('shree')).toBe('shri');
    expect(foldLatin('raam')).toBe('ram');
    expect(foldLatin('vishwaroop')).toBe('vishvarup');
  });

  it('leaves Devanagari untouched', () => {
    expect(foldLatin('राम')).toBe('राम');
  });
});

describe('buildSearchKeywords', () => {
  const keywords = buildSearchKeywords({
    title: 'Shri Ganesh Darshan',
    tags: ['Vinayak', 'गणपति'],
    extra: ['Shri Ganesh', 'श्री गणेश'],
  });

  it('contains prefixes of every word', () => {
    for (const k of ['sh', 'shr', 'shri', 'ga', 'gan', 'ganesh', 'da', 'darshan', 'vi', 'vinayak']) {
      expect(keywords).toContain(k);
    }
  });

  it('contains Devanagari prefixes', () => {
    expect(keywords).toContain('गण');
    expect(keywords).toContain('गणपति');
    expect(keywords).toContain('श्री');
  });

  it('stems the trailing inherent vowel', () => {
    expect(stemLatin('ganesha')).toBe('ganesh');
    expect(stemLatin('ram')).toBe('ram');
    expect(buildSearchKeywords({ title: 'Ganesha' })).toContain('ganesh');
  });

  it('never contains single characters and stays under the cap', () => {
    expect(keywords.every((k) => Array.from(k).length >= 2)).toBe(true);
    expect(keywords.length).toBeLessThanOrEqual(250);
  });
});

describe('parseSearchQuery', () => {
  it('picks the longest term for the server and keeps all terms', () => {
    const q = parseSearchQuery('Shree Ganesha');
    expect(q.term).toBe('ganesh');
    expect(q.terms).toEqual(['shri', 'ganesh']);
  });

  it('returns null for input that is too short', () => {
    expect(parseSearchQuery(' a ').term).toBeNull();
  });

  it('matches documents built from variant spellings', () => {
    const doc = buildSearchKeywords({ title: 'Shri Ram Darbar' });
    expect(matchesAllTerms(doc, parseSearchQuery('raam darbaar').terms)).toBe(true);
    expect(matchesAllTerms(doc, parseSearchQuery('shree rama').terms)).toBe(true);
    expect(matchesAllTerms(doc, parseSearchQuery('krishna').terms)).toBe(false);
    const shiva = buildSearchKeywords({ title: 'Har Har Mahadev', tags: ['Shiv'] });
    expect(matchesAllTerms(shiva, parseSearchQuery('shiva').terms)).toBe(true);
    expect(matchesAllTerms(shiva, parseSearchQuery('mahad').terms)).toBe(true);
  });
});
