import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { ScrollView, View } from 'react-native';
import { PRIVACY_POLICY, TERMS_OF_USE } from '@devdarshan/shared/legal';
import { AppText, ScreenHeader, useTheme } from '@devdarshan/ui';
import type { RootStackParamList } from '../navigation/types';

export function LegalScreen() {
  const navigation = useNavigation();
  const { params } = useRoute<RouteProp<RootStackParamList, 'Legal'>>();
  const { colors, spacing } = useTheme();
  const doc = params.document === 'terms' ? TERMS_OF_USE : PRIVACY_POLICY;
  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScreenHeader title={doc.title} subtitle={`Updated ${doc.updated}`} onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xxxl }}>
        {doc.sections.map((section) => (
          <View key={section.heading} style={{ marginBottom: spacing.xl }}>
            <AppText variant="subheading" style={{ marginBottom: spacing.xs }}>
              {section.heading}
            </AppText>
            <AppText variant="body" color="textMuted">
              {section.body}
            </AppText>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}
