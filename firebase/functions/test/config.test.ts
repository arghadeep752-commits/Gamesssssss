import { createHash } from 'node:crypto';
import { afterEach, describe, expect, it } from 'vitest';
import { hasBootstrapAdmin, isBootstrapAdminEmail } from '../src/config';

const sha256 = (value: string) => createHash('sha256').update(value, 'utf8').digest('hex');

describe('bootstrap admin matching', () => {
  afterEach(() => {
    delete process.env.DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL_SHA256;
    delete process.env.DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL;
  });

  it('matches the SHA-256 of the normalised email', () => {
    process.env.DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL_SHA256 = sha256('first.admin@example.com');
    expect(hasBootstrapAdmin()).toBe(true);
    expect(isBootstrapAdminEmail('First.Admin@Example.com ')).toBe(true);
    expect(isBootstrapAdminEmail('someone.else@example.com')).toBe(false);
    expect(isBootstrapAdminEmail('')).toBe(false);
    expect(isBootstrapAdminEmail(null)).toBe(false);
  });

  it('prefers the hash over a plain email', () => {
    process.env.DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL_SHA256 = sha256('first.admin@example.com');
    process.env.DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL = 'other@example.com';
    expect(isBootstrapAdminEmail('other@example.com')).toBe(false);
    expect(isBootstrapAdminEmail('first.admin@example.com')).toBe(true);
  });

  it('accepts a plain email when no hash is set', () => {
    process.env.DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL = ' First.Admin@example.com ';
    expect(isBootstrapAdminEmail('first.admin@EXAMPLE.com')).toBe(true);
    expect(isBootstrapAdminEmail('first.admin@example.co')).toBe(false);
  });

  it('allows nobody when nothing is configured', () => {
    expect(hasBootstrapAdmin()).toBe(false);
    expect(isBootstrapAdminEmail('first.admin@example.com')).toBe(false);
  });
});
