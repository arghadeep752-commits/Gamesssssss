import { APP_INFO } from './appInfo';

/**
 * Legal copy. These statements describe this codebase as shipped: no network
 * code, no accounts, no analytics, advertising or crash-reporting SDKs, and
 * Android backup disabled (app.json "allowBackup": false). If you add any SDK
 * or network feature, update this text before release.
 */
export interface LegalSection {
  readonly heading: string;
  readonly body: string;
}

export interface LegalDoc {
  readonly title: string;
  readonly updated: string;
  readonly sections: readonly LegalSection[];
}

const { name, developerName, contactEmail, policyDate, version } = APP_INFO;

export const PRIVACY_POLICY: LegalDoc = {
  title: 'Privacy Policy',
  updated: policyDate,
  sections: [
    {
      heading: 'Summary',
      body: `${name} is an offline puzzle game. It has no accounts, no advertising, no analytics and no crash reporting, and the game does not send any information over the internet.`,
    },
    {
      heading: 'What is stored on your device',
      body: 'To keep your progress, the game saves a small file in its own private storage on this device: unlocked levels, best results and stars, hints, daily challenge records and streaks, achievements, your settings, the profile name you choose, and, if you allow it in Privacy Preferences, the puzzle you are currently playing. This data never leaves your device through the game.',
    },
    {
      heading: 'Backups',
      body: 'The app opts out of Android app-data backup, so your game data is not copied to cloud backups by the system.',
    },
    {
      heading: 'Permissions',
      body: 'Vibration is used for optional haptic feedback. Audio settings access is required by the sound library to play effects and music. The internet permission is included by the React Native framework that the app is built with; the game itself makes no network requests. The game does not request access to your microphone, location, contacts, camera or files.',
    },
    {
      heading: 'Deleting your data',
      body: 'Use Me > Delete Local Game Data to erase everything the game has saved. Uninstalling the app also removes it.',
    },
    {
      heading: 'Children',
      body: 'The game does not collect personal information from anyone, including children.',
    },
    {
      heading: 'Changes and contact',
      body: `If this policy changes, the updated version will ship with the app. Questions: ${developerName}, ${contactEmail}.`,
    },
  ],
};

export const TERMS: LegalDoc = {
  title: 'Terms of Service',
  updated: policyDate,
  sections: [
    {
      heading: 'Using the game',
      body: `${name} is provided for personal entertainment. You may install and play it on devices you own or control.`,
    },
    {
      heading: 'Ownership',
      body: `The game, its levels, artwork and sounds are owned by ${developerName}. You may not resell, redistribute or claim them as your own.`,
    },
    {
      heading: 'Your progress',
      body: 'Progress is stored only on your device. It can be lost if you delete the app or its data, and it cannot be restored by the developer.',
    },
    {
      heading: 'No warranty',
      body: 'The game is provided "as is" without warranties of any kind. To the extent permitted by law, the developer is not liable for any loss arising from its use.',
    },
    {
      heading: 'Changes',
      body: 'These terms may be updated in a future version of the app. Continuing to play after an update means you accept the updated terms.',
    },
    {
      heading: 'Contact',
      body: `${developerName}, ${contactEmail}.`,
    },
  ],
};

export const ABOUT: LegalDoc = {
  title: 'About',
  updated: `Version ${version}`,
  sections: [
    {
      heading: name,
      body: 'A calm, minimalist logic puzzle. Every arrow slides out the way it points, but only if nothing stands in its path. Find the right order and clear the board.',
    },
    {
      heading: 'Inside',
      body: '100 verified levels across five difficulty tiers, a new daily challenge every day, hints that always show a correct move, and a path scanner that explains what blocks an arrow. Everything works offline.',
    },
    {
      heading: 'Made by',
      body: `${developerName}. Built with React Native and Expo. All artwork and sounds are original to this game.`,
    },
  ],
};
