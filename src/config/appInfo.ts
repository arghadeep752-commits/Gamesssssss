/**
 * App identity and publisher details. The developer fields are placeholders:
 * replace them with real details before publishing. Every legal screen reads
 * from here, so nothing else needs editing.
 */
export const APP_INFO = {
  name: 'Arrow Flow',
  /** Keep in sync with "version" in app.json. */
  version: '1.0.0',
  developerName: '[Developer name]',
  contactEmail: '[contact email]',
  /** Date the privacy policy and terms below were last revised. */
  policyDate: '28 October 2026',
} as const;

export const STORAGE_KEYS = {
  save: 'arrowflow.save',
  backup: 'arrowflow.save.backup',
} as const;
