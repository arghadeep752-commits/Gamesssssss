import { nativeErrorCode, nativeErrorMessage } from '@devdarshan/native';

export interface FriendlyError {
  title: string;
  message: string;
  /** User-initiated cancellations need no message at all. */
  silent: boolean;
}

/** Firebase errors carry codes like "auth/network-request-failed" or "firestore/unavailable". */
function firebaseCode(error: unknown): string | null {
  const code = nativeErrorCode(error);
  return code && code.includes('/') ? code : null;
}

export function describeError(error: unknown): FriendlyError {
  const code = nativeErrorCode(error) ?? '';
  const fb = firebaseCode(error);
  const raw = nativeErrorMessage(error);

  switch (code) {
    case 'E_CANCELLED':
    case 'E_SIGNIN_CANCELLED':
      return { title: 'Cancelled', message: '', silent: true };
    case 'E_NETWORK':
    case 'E_HTTP':
      return { title: 'No connection', message: 'Check your internet connection and try again.', silent: false };
    case 'E_NO_SPACE':
      return { title: 'Storage full', message: 'Free up some space on your phone and try again.', silent: false };
    case 'E_INVALID_IMAGE':
      return { title: 'Image problem', message: 'This wallpaper could not be loaded. Please try another one.', silent: false };
    case 'E_WALLPAPER_NOT_ALLOWED':
      return {
        title: 'Not allowed on this phone',
        message: 'Your phone blocks wallpaper changes (for example a work or school policy).',
        silent: false,
      };
    case 'E_WALLPAPER_UNSUPPORTED':
      return { title: 'Not supported', message: 'This device does not support wallpapers.', silent: false };
    case 'E_WALLPAPER_FAILED':
      return { title: 'Could not set wallpaper', message: raw, silent: false };
    case 'E_PERMISSION_REQUIRED':
      return { title: 'Permission needed', message: 'Allow storage access to save wallpapers on this Android version.', silent: false };
    case 'E_SAVE_FAILED':
      return { title: 'Could not save', message: raw, silent: false };
    case 'E_SHARE_FAILED':
      return { title: 'Could not share', message: raw, silent: false };
    case 'E_SIGNIN_NO_ACCOUNT':
      return { title: 'No Google account', message: 'Add a Google account in your phone Settings → Accounts, then try again.', silent: false };
    case 'E_SIGNIN_CONFIG':
    case 'SIGNIN_NOT_CONFIGURED':
      return {
        title: 'Sign-in not set up yet',
        message: "Google sign-in isn't configured for this build yet. Browsing and downloads still work.",
        silent: false,
      };
    case 'E_SIGNIN_UNSUPPORTED':
      return { title: 'Update Google Play services', message: 'Google sign-in needs an up-to-date Google Play services app.', silent: false };
    case 'E_SIGNIN_INTERRUPTED':
      return { title: 'Sign-in interrupted', message: 'Please try again.', silent: false };
    case 'E_UNAVAILABLE':
      return { title: 'Not available', message: raw, silent: false };
    default:
      break;
  }

  if (fb) {
    if (fb.endsWith('network-request-failed') || fb.endsWith('unavailable') || fb.endsWith('deadline-exceeded')) {
      return { title: 'No connection', message: 'Check your internet connection and try again.', silent: false };
    }
    if (fb.endsWith('operation-not-allowed')) {
      return { title: 'Sign-in disabled', message: 'Google sign-in is turned off for this app right now.', silent: false };
    }
    if (fb.endsWith('permission-denied') || fb.endsWith('not-found')) {
      return { title: 'Not available', message: 'This content is no longer available.', silent: false };
    }
    if (fb.endsWith('user-disabled')) {
      return { title: 'Account disabled', message: 'This account has been disabled.', silent: false };
    }
  }

  return { title: 'Something went wrong', message: raw || 'Please try again.', silent: false };
}

export class AppError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'AppError';
  }
}
