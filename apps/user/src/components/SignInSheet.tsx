import { View } from 'react-native';
import { create } from 'zustand';
import { AppText, Button, Sheet, useTheme, useToast } from '@devdarshan/ui';
import { useAuth } from '../data/auth';
import { describeError } from '../errors';

interface SignInPromptState {
  visible: boolean;
  reason: string;
  open: (reason?: string) => void;
  close: () => void;
}

export const useSignInPrompt = create<SignInPromptState>((set) => ({
  visible: false,
  reason: '',
  open: (reason = 'Sign in to keep your liked wallpapers in sync across your phones.') => set({ visible: true, reason }),
  close: () => set({ visible: false }),
}));

/** Rendered once at the root; any screen can ask for sign-in with useSignInPrompt().open(). */
export function SignInSheet() {
  const { visible, reason, close } = useSignInPrompt();
  const { signIn, signingIn } = useAuth();
  const toast = useToast();
  const { spacing } = useTheme();

  const onSignIn = async () => {
    try {
      await signIn();
      close();
      toast.show({ tone: 'success', message: 'Signed in', detail: 'Your likes now sync across your devices.' });
    } catch (error) {
      const friendly = describeError(error);
      if (!friendly.silent) toast.show({ tone: 'error', message: friendly.title, detail: friendly.message });
    }
  };

  return (
    <Sheet visible={visible} onClose={close} title="Sign in with Google" dismissable={!signingIn}>
      <View style={{ paddingHorizontal: spacing.xl, gap: spacing.md }}>
        <AppText variant="body" color="textMuted">
          {reason}
        </AppText>
        <AppText variant="caption" color="textSubtle">
          We only use your name, email and photo to show your profile. Browsing never needs an account.
        </AppText>
        <Button title="Continue with Google" icon="logIn" onPress={onSignIn} loading={signingIn} fullWidth testID="google-sign-in" />
        <Button title="Not now" variant="ghost" onPress={close} disabled={signingIn} fullWidth />
      </View>
    </Sheet>
  );
}
