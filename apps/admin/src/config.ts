import Constants from 'expo-constants';

interface BuildExtra {
  variant?: string;
  versionCode?: number;
  firebaseProjectId?: string | null;
  googleWebClientId?: string | null;
  buildChannel?: string;
  gitSha?: string | null;
}

const extra = (Constants.expoConfig?.extra ?? {}) as BuildExtra;

export const buildInfo = {
  version: Constants.expoConfig?.version ?? '1.0.0',
  versionCode: extra.versionCode ?? 1,
  channel: extra.buildChannel ?? 'local',
  gitSha: extra.gitSha ?? null,
  googleWebClientId: extra.googleWebClientId ?? null,
};

export function versionLabel(): string {
  const parts = [`${buildInfo.version} (${buildInfo.versionCode})`];
  if (buildInfo.channel !== 'release') parts.push(buildInfo.channel);
  if (buildInfo.gitSha) parts.push(buildInfo.gitSha);
  return parts.join(' · ');
}
