export interface LegalSection {
  heading: string;
  body: string;
}

export interface LegalDocument {
  title: string;
  updated: string;
  sections: LegalSection[];
}

/**
 * In-app privacy policy. It describes exactly what this codebase does; update it
 * if you add analytics, ads or any new data collection. Google Play also needs a
 * public URL for this text (see docs/PRIVACY-POLICY.md).
 */
export const PRIVACY_POLICY: LegalDocument = {
  title: 'Privacy Policy',
  updated: '21 October 2026',
  sections: [
    {
      heading: 'Summary',
      body:
        'DevDarshan lets you browse devotional wallpapers without an account. If you choose to sign in with Google, we store only what is needed to sync your liked wallpapers. We do not show ads, sell data or track you across other apps.',
    },
    {
      heading: 'Information we collect',
      body:
        'Without signing in: no personal information. The app downloads wallpapers and counts downloads anonymously (a number per wallpaper, not linked to you).\n\nWith Google sign-in: your Google account ID, email address, name and profile photo URL (provided by Google), and the list of wallpapers you have liked.',
    },
    {
      heading: 'How we use it',
      body:
        'Your account identifies you so your liked wallpapers sync across your devices. Your name and photo are shown only to you, on your profile screen. We do not use your data for advertising.',
    },
    {
      heading: 'Device permissions',
      body:
        'Set wallpaper: lets the app change your home or lock screen when you ask it to.\nStorage (Android 9 and older only): saves wallpapers you download to Pictures/DevDarshan. Newer Android versions need no storage permission.\nInternet: loads wallpapers.',
    },
    {
      heading: 'Service providers',
      body:
        'DevDarshan runs on Google Firebase (Authentication, Cloud Firestore, Cloud Storage, Cloud Functions and App Check). Google processes this data on our behalf under its own privacy terms. Sharing a wallpaper hands the image to the app you choose, such as WhatsApp.',
    },
    {
      heading: 'Retention and deletion',
      body:
        'Your account and likes are kept until you delete them. Profile → Delete account removes your sign-in account and your liked-wallpaper list immediately. Wallpapers you saved to your gallery stay on your phone.',
    },
    {
      heading: 'Children',
      body: 'DevDarshan is suitable for all ages and does not knowingly collect personal information from children.',
    },
    {
      heading: 'Contact',
      body: 'Questions or requests: use Profile → Send feedback, or write to the support email listed in the app.',
    },
  ],
};

export const TERMS_OF_USE: LegalDocument = {
  title: 'Terms of Use',
  updated: '21 October 2026',
  sections: [
    {
      heading: 'Personal, devotional use',
      body:
        'Wallpapers are provided for personal, non-commercial use on your own devices. Please do not resell them or present them as your own work.',
    },
    {
      heading: 'Respectful use',
      body:
        'These images depict sacred figures and symbols. Please use and share them respectfully and do not edit them in ways that would offend devotees.',
    },
    {
      heading: 'Content ownership',
      body:
        'Artwork belongs to its respective creators. If you believe a wallpaper infringes your rights, contact us through Profile → Send feedback and we will review and remove it where appropriate.',
    },
    {
      heading: 'Your account',
      body:
        'Signing in is optional. You are responsible for activity on your Google account. You can delete your DevDarshan account at any time from your profile.',
    },
    {
      heading: 'No warranty',
      body:
        'The app is provided as is. Some phones restrict lock-screen wallpapers or manage them through their own theme apps; DevDarshan reports exactly what your phone allowed.',
    },
    {
      heading: 'Changes',
      body: 'We may update these terms. Continued use after an update means you accept the revised terms.',
    },
  ],
};
