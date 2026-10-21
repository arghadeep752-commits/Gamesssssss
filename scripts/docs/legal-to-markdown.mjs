// Regenerates docs/PRIVACY-POLICY.md and docs/TERMS-OF-USE.md from the in-app text
// (packages/shared/src/legal.ts), so the public copies never drift from the app.
//
//   node --experimental-strip-types scripts/docs/legal-to-markdown.mjs
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const { PRIVACY_POLICY, TERMS_OF_USE } = await import(join(root, 'packages/shared/src/legal.ts'));

function render(doc, appName) {
  const lines = [`# ${appName} ${doc.title}`, '', `_Last updated: ${doc.updated}_`, ''];
  for (const section of doc.sections) {
    lines.push(`## ${section.heading}`, '');
    for (const paragraph of section.body.split('\n\n')) {
      const rows = paragraph.split('\n');
      if (rows.length > 1) rows.forEach((row) => lines.push(`- ${row}`));
      else lines.push(paragraph);
      lines.push('');
    }
  }
  lines.push('---', '', '_This file is generated from `packages/shared/src/legal.ts` by `scripts/docs/legal-to-markdown.mjs`; edit the source, not this file._', '');
  return lines.join('\n');
}

writeFileSync(join(root, 'docs/PRIVACY-POLICY.md'), render(PRIVACY_POLICY, 'DevDarshan'));
writeFileSync(join(root, 'docs/TERMS-OF-USE.md'), render(TERMS_OF_USE, 'DevDarshan'));
console.log('Wrote docs/PRIVACY-POLICY.md and docs/TERMS-OF-USE.md');
