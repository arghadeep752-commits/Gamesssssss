// Writes a syntactically valid google-services.json for builds made before a real
// Firebase project is connected. The apps detect the placeholder project id and
// show a "not connected yet" screen instead of pretending to work.
//
//   node scripts/ci/placeholder-google-services.mjs <output-path>
import { writeFileSync } from 'node:fs';

const out = process.argv[2];
if (!out) {
  console.error('usage: placeholder-google-services.mjs <output-path>');
  process.exit(1);
}

const projectId = 'devdarshan-not-configured';
const client = (packageName, n) => ({
  client_info: {
    mobilesdk_app_id: `1:000000000000:android:00000000000000000000${n}`,
    android_client_info: { package_name: packageName },
  },
  oauth_client: [],
  api_key: [{ current_key: 'AIzaSyPlaceholderKeyNotConfigured000000' }],
  services: { appinvite_service: { other_platform_oauth_client: [] } },
});

const json = {
  project_info: {
    project_number: '000000000000',
    project_id: projectId,
    storage_bucket: `${projectId}.firebasestorage.app`,
  },
  client: [client('com.devdarshan.wallpapers', 1), client('com.devdarshan.admin', 2)],
  configuration_version: '1',
};

writeFileSync(out, `${JSON.stringify(json, null, 2)}\n`);
console.log(`placeholder google-services.json written to ${out}`);
