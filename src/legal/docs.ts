/**
 * In-app legal pages. Keep these accurate if the app ever changes: they describe
 * an offline game with no accounts, ads, analytics or network access.
 */
export const APP_INFO = {
  name: 'Arrow Flow',
  developer: 'Arghadeep Das',
  /** Contact email for privacy questions. Leave empty to point people to the Play Store listing. */
  contactEmail: '',
  version: '3.0.0',
  effective: 'November 28, 2026',
  country: 'India',
} as const;

export interface LegalSection {
  readonly h?: string;
  readonly p: readonly string[];
}

export interface LegalDoc {
  readonly title: string;
  readonly updated?: string;
  readonly sections: readonly LegalSection[];
}

export type LegalId = 'privacy' | 'terms' | 'licenses' | 'about';

const contactLine = APP_INFO.contactEmail
  ? `Email: ${APP_INFO.contactEmail}`
  : 'Use the developer contact email shown on the Arrow Flow page in the Google Play Store.';

const PRIVACY: LegalDoc = {
  title: 'Privacy Policy',
  updated: `Effective ${APP_INFO.effective}`,
  sections: [
    {
      p: [
        `This Privacy Policy explains how ${APP_INFO.name} (the "app"), developed by ${APP_INFO.developer} ("we", "us"), handles information when you use it.`,
        'In short: the app does not collect, transmit, share or sell any personal data. It works completely offline and has no accounts, no advertising, no analytics and no tracking.',
      ],
    },
    {
      h: 'Information we collect',
      p: [
        'None. We do not collect your name, email address, phone number, location, contacts, photos, files, device identifiers, advertising ID, IP address or any usage or crash analytics.',
      ],
    },
    {
      h: 'Information stored on your device',
      p: [
        'To let you continue where you left off, the app saves your game progress (levels cleared, coins, hints, collected shapes, daily challenge results, statistics) and your settings in the app\'s private storage on your device.',
        'This information never leaves your device and we cannot access it. The app opts out of Android cloud backup, so it is not copied to any server. You can delete it at any time with Settings > Reset progress, or by uninstalling the app.',
      ],
    },
    {
      h: 'Permissions',
      p: [
        'The app uses only the vibration permission, for optional haptic feedback that you can switch off in Settings. It does not request internet access, so it cannot send any information anywhere.',
      ],
    },
    {
      h: 'Third-party services',
      p: [
        'The app contains no third-party advertising, analytics, social or tracking services. It is built with open-source software libraries that run entirely on your device (listed under Licenses & Credits).',
      ],
    },
    {
      h: 'Children\'s privacy',
      p: [
        'The app is suitable for all ages. Because it collects no personal information from anyone, it does not collect personal information from children under 13 (or the equivalent minimum age in your country).',
      ],
    },
    {
      h: 'Your rights',
      p: [
        'Privacy laws such as the GDPR (EU/UK), the CCPA/CPRA (California) and India\'s Digital Personal Data Protection Act, 2023 give you rights over personal data held about you. We hold no personal data about you, so there is nothing for us to access, correct, export or delete. The data on your device is fully under your control.',
      ],
    },
    {
      h: 'Security',
      p: ['Your saved progress stays inside the app\'s private storage, which Android protects from other apps.'],
    },
    {
      h: 'Changes to this policy',
      p: [
        'If the app ever changes the way it handles information, this policy will be updated before that change takes effect, and the effective date above will change. The latest version is always available in the app.',
      ],
    },
    { h: 'Contact', p: [`Questions about this policy: ${APP_INFO.developer}.`, contactLine] },
  ],
};

const TERMS: LegalDoc = {
  title: 'Terms of Use',
  updated: `Effective ${APP_INFO.effective}`,
  sections: [
    {
      p: [
        `These Terms of Use ("Terms") apply to your use of ${APP_INFO.name} (the "app"), provided by ${APP_INFO.developer}. By installing or using the app you agree to these Terms. If you do not agree, please do not use the app.`,
      ],
    },
    {
      h: 'Your licence',
      p: [
        'We grant you a personal, non-exclusive, non-transferable, revocable licence to install and use the app on devices you own or control, for your own non-commercial entertainment.',
      ],
    },
    {
      h: 'What you may not do',
      p: [
        'You may not copy, modify, sell, rent, sublicense or redistribute the app; remove any copyright or proprietary notices; or use the app in any unlawful way. You may not decompile or reverse engineer the app except where applicable law expressly allows it.',
      ],
    },
    {
      h: 'Coins, hints and themes',
      p: [
        'Coins, hints, themes and other in-game items are earned by playing. They have no monetary value, cannot be bought, sold, exchanged or redeemed for money or anything of value, and exist only on your device. They are removed if you reset your progress or uninstall the app.',
      ],
    },
    {
      h: 'Intellectual property',
      p: [
        `The app, including its puzzles, level designs, graphics, text and code, is © 2026 ${APP_INFO.developer}. All rights reserved except as stated in these Terms. Third-party components are used under their own licences, listed under Licenses & Credits.`,
      ],
    },
    {
      h: 'Disclaimer',
      p: [
        'The app is provided "as is" and "as available", without warranties of any kind, whether express or implied, including fitness for a particular purpose and non-infringement. We do not guarantee that the app will be error-free or uninterrupted.',
      ],
    },
    {
      h: 'Limitation of liability',
      p: [
        'To the fullest extent permitted by law, the developer is not liable for any indirect, incidental, special or consequential damages, or for any loss of data or progress, arising from your use of or inability to use the app. Nothing in these Terms limits liability that cannot be limited under applicable law.',
      ],
    },
    {
      h: 'Changes',
      p: ['We may update these Terms from time to time. The updated Terms will be available in the app, and continuing to use the app after an update means you accept them.'],
    },
    {
      h: 'Governing law',
      p: [`These Terms are governed by the laws of ${APP_INFO.country}, without regard to its conflict-of-law rules, except where the law of your country of residence requires otherwise.`],
    },
    { h: 'Contact', p: [contactLine] },
  ],
};

const MIT =
  'Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.';

const LICENSES: LegalDoc = {
  title: 'Licenses & Credits',
  sections: [
    {
      h: 'Sound effects',
      p: [
        '"Interface Sounds" by Kenney (www.kenney.nl), released under Creative Commons Zero (CC0 1.0 Universal, public domain dedication). Thank you, Kenney!',
      ],
    },
    {
      h: 'Artwork',
      p: ['The logo, icons, board shapes and all puzzles are original to Arrow Flow.'],
    },
    {
      h: 'Open-source software (MIT License)',
      p: [
        'React and React Native — Copyright (c) Meta Platforms, Inc. and affiliates.',
        'Hermes JavaScript engine — Copyright (c) Meta Platforms, Inc. and affiliates.',
        'Expo SDK and modules (expo, expo-audio, expo-haptics, expo-splash-screen, expo-status-bar, expo-navigation-bar, expo-system-ui, expo-asset, expo-build-properties) — Copyright (c) 650 Industries, Inc. (Expo).',
        'react-native-reanimated, react-native-worklets and react-native-gesture-handler — Copyright (c) Software Mansion.',
        'react-native-svg — Copyright (c) the react-native-svg contributors.',
        'react-native-safe-area-context — Copyright (c) Th3rdwave.',
        '@react-native-async-storage/async-storage — Copyright (c) the React Native Community.',
      ],
    },
    { h: 'MIT License', p: [MIT] },
  ],
};

const ABOUT: LegalDoc = {
  title: 'About',
  sections: [
    {
      p: [
        `${APP_INFO.name} ${APP_INFO.version}`,
        `Made by ${APP_INFO.developer}.`,
        'A calm but tricky puzzle: every board is a picture packed with snake-shaped arrows. Tap an arrow and it slides out the way it points, but only if nothing stands in its way. Find the right order and clear the board.',
        'Fully offline. No ads, no accounts, no tracking.',
      ],
    },
    { h: 'Support', p: [contactLine] },
  ],
};

export const LEGAL_DOCS: Record<LegalId, LegalDoc> = { privacy: PRIVACY, terms: TERMS, licenses: LICENSES, about: ABOUT };
