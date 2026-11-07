import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/theme.dart';
import 'core/widgets.dart';
import 'features/auth/auth_screens.dart';
import 'features/calls/call_screens.dart';
import 'features/chats/chat_list_screen.dart';
import 'features/chats/chat_screen.dart';
import 'features/chats/extra_screens.dart';
import 'features/communities/communities.dart';
import 'features/contacts/contacts.dart';
import 'features/groups/groups.dart';
import 'features/home/home_shell.dart';
import 'features/profile/profile_screens.dart';
import 'features/search/search_screen.dart';
import 'features/settings/settings_screens.dart';
import 'features/updates/updates.dart';
import 'services/session.dart';

final sharedPrefsProvider = Provider<SharedPreferences>((ref) => throw UnimplementedError());

class ThemeModeController extends StateNotifier<ThemeMode> {
  ThemeModeController(this.prefs) : super(_read(prefs));
  final SharedPreferences prefs;

  static ThemeMode _read(SharedPreferences p) =>
      ThemeMode.values.firstWhere((m) => m.name == p.getString('theme_mode'), orElse: () => ThemeMode.system);

  void set(ThemeMode mode) {
    state = mode;
    prefs.setString('theme_mode', mode.name);
  }
}

final themeModeProvider =
    StateNotifierProvider<ThemeModeController, ThemeMode>((ref) => ThemeModeController(ref.watch(sharedPrefsProvider)));

class HimeApp extends ConsumerStatefulWidget {
  const HimeApp({super.key});

  @override
  ConsumerState<HimeApp> createState() => _HimeAppState();
}

class _HimeAppState extends ConsumerState<HimeApp> {
  late final GoRouter _router = buildRouter(ref.read(sessionProvider));

  @override
  Widget build(BuildContext context) {
    final mode = ref.watch(themeModeProvider);
    return MaterialApp.router(
      title: 'Hime',
      debugShowCheckedModeBanner: false,
      theme: HimeTheme.light(),
      darkTheme: HimeTheme.dark(),
      themeMode: mode,
      routerConfig: _router,
    );
  }
}

const _authPaths = {'/welcome', '/auth/email', '/auth/phone', '/auth/otp', '/auth/forgot', '/auth/verify-email'};

CustomTransitionPage<void> _page(GoRouterState state, Widget child) => CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionDuration: const Duration(milliseconds: 260),
      reverseTransitionDuration: const Duration(milliseconds: 220),
      transitionsBuilder: (context, animation, secondary, child) {
        final curved = CurvedAnimation(parent: animation, curve: Curves.easeOutCubic);
        return FadeTransition(
          opacity: curved,
          child: SlideTransition(
            position: Tween(begin: const Offset(0.06, 0), end: Offset.zero).animate(curved),
            child: child,
          ),
        );
      },
    );

GoRoute _r(String path, Widget Function(GoRouterState s) build) =>
    GoRoute(path: path, pageBuilder: (context, state) => _page(state, build(state)));

GoRouter buildRouter(SessionController session) {
  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: session,
    // Deep links that aren't app routes (e.g. the auth callback, which
    // supabase_flutter handles itself) just land on the home screen.
    onException: (context, state, router) => router.go('/chats'),
    redirect: (context, state) {
      final loc = state.matchedLocation;
      switch (session.stage) {
        case SessionStage.loading:
          return loc == '/splash' ? null : '/splash';
        case SessionStage.signedOut:
          return _authPaths.contains(loc) ? null : '/welcome';
        case SessionStage.needsMfa:
          return loc == '/auth/mfa' ? null : '/auth/mfa';
        case SessionStage.recovery:
          return loc == '/auth/reset-password' ? null : '/auth/reset-password';
        case SessionStage.needsOnboarding:
          return loc == '/onboarding' ? null : '/onboarding';
        case SessionStage.error:
          return loc == '/error' ? null : '/error';
        case SessionStage.ready:
          if (loc == '/splash' || loc == '/onboarding' || loc == '/error' || loc.startsWith('/auth') || loc == '/welcome') {
            return '/chats';
          }
          return null;
      }
    },
    routes: [
      GoRoute(path: '/', redirect: (_, __) => '/chats'),
      GoRoute(path: '/splash', builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/error', builder: (_, __) => const StartupErrorScreen()),
      _r('/welcome', (_) => const WelcomeScreen()),
      _r('/auth/email', (s) => EmailAuthScreen(signUp: s.uri.queryParameters['mode'] == 'signup')),
      _r('/auth/phone', (_) => const PhoneAuthScreen()),
      _r('/auth/otp', (s) => OtpScreen(args: s.extra as OtpArgs)),
      _r('/auth/forgot', (s) => ForgotPasswordScreen(email: s.extra as String?)),
      _r('/auth/verify-email', (s) => VerifyEmailScreen(email: (s.extra as String?) ?? '')),
      _r('/auth/mfa', (_) => const MfaVerifyScreen()),
      _r('/auth/reset-password', (_) => const ResetPasswordScreen()),
      _r('/onboarding', (_) => const OnboardingScreen()),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => HomeShell(shell: shell),
        branches: [
          StatefulShellBranch(routes: [GoRoute(path: '/chats', builder: (_, __) => const ChatListScreen())]),
          StatefulShellBranch(routes: [GoRoute(path: '/updates', builder: (_, __) => const UpdatesScreen())]),
          StatefulShellBranch(routes: [GoRoute(path: '/communities', builder: (_, __) => const CommunitiesScreen())]),
          StatefulShellBranch(routes: [GoRoute(path: '/calls', builder: (_, __) => const CallsScreen())]),
          StatefulShellBranch(routes: [GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen())]),
        ],
      ),
      _r('/chat/:id', (s) => ChatScreen(conversationId: s.pathParameters['id']!)),
      _r('/chat/:id/info', (s) => ChatInfoScreen(conversationId: s.pathParameters['id']!)),
      _r('/chat/:id/media', (s) => MediaGalleryScreen(conversationId: s.pathParameters['id']!)),
      _r('/chat/:id/search', (s) => ChatSearchScreen(conversationId: s.pathParameters['id']!)),
      _r('/user/:id', (s) => UserProfileScreen(userId: s.pathParameters['id']!)),
      _r('/new-chat', (_) => const NewChatScreen()),
      _r('/new-group', (s) => CreateGroupScreen(communityId: s.uri.queryParameters['community'])),
      _r('/group/:id/add', (s) => AddMembersScreen(conversationId: s.pathParameters['id']!)),
      _r('/group/:id/invite', (s) => GroupInviteScreen(conversationId: s.pathParameters['id']!)),
      _r('/join', (s) => JoinInviteScreen(code: s.uri.queryParameters['code'], community: s.uri.queryParameters['c'] == '1')),
      _r('/search', (_) => const SearchScreen()),
      _r('/starred', (_) => const StarredScreen()),
      _r('/archived', (_) => const ArchivedScreen()),
      _r('/forward', (s) => ForwardScreen(messages: s.extra as ForwardArgs)),
      _r('/message-info', (s) => MessageInfoScreen(args: s.extra as MessageInfoArgs)),
      _r('/viewer', (s) => MediaViewerScreen(args: s.extra as MediaViewerArgs)),
      _r('/profile/edit', (_) => const EditProfileScreen()),
      _r('/contacts', (_) => const ContactsScreen()),
      _r('/blocked', (_) => const BlockedScreen()),
      _r('/community/new', (_) => const CreateCommunityScreen()),
      _r('/community/:id', (s) => CommunityScreen(communityId: s.pathParameters['id']!)),
      _r('/status/compose', (_) => const TextStatusComposer()),
      _r('/status/view', (s) => StatusViewerScreen(args: s.extra as StatusViewerArgs)),
      _r('/status/privacy', (_) => const StatusPrivacyScreen()),
      GoRoute(
        path: '/call',
        pageBuilder: (context, state) => CustomTransitionPage<void>(
          key: state.pageKey,
          child: const CallScreen(),
          transitionsBuilder: (_, a, __, child) => FadeTransition(opacity: a, child: child),
        ),
      ),
      _r('/settings/account', (_) => const AccountScreen()),
      _r('/settings/privacy', (_) => const PrivacyScreen()),
      _r('/settings/security', (_) => const SecurityScreen()),
      _r('/settings/two-step', (_) => const TwoStepScreen()),
      _r('/settings/devices', (_) => const DevicesScreen()),
      _r('/settings/notifications', (_) => const NotificationSettingsScreen()),
      _r('/settings/chats', (_) => const ChatSettingsScreen()),
      _r('/settings/storage', (_) => const StorageScreen()),
      _r('/settings/appearance', (_) => const AppearanceScreen()),
      _r('/settings/language', (_) => const LanguageScreen()),
      _r('/settings/help', (_) => const HelpScreen()),
      _r('/settings/about', (_) => const AboutScreen()),
      _r('/settings/legal/:doc', (s) => LegalScreen(doc: s.pathParameters['doc']!)),
      _r('/settings/delete-account', (_) => const DeleteAccountScreen()),
    ],
  );
}

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: HimeColors.yellow,
      body: Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Image.asset('assets/images/hime_mark.png', width: 96, height: 96),
          const SizedBox(height: 28),
          const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: HimeColors.ink)),
        ]),
      ),
    );
  }
}

class StartupErrorScreen extends ConsumerWidget {
  const StartupErrorScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionProvider);
    return Scaffold(
      body: SafeArea(
        child: Column(children: [
          Expanded(child: ErrorState(error: session.error ?? 'Unknown error', onRetry: session.retry)),
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextButton(onPressed: () => session.signOut(), child: const Text('Sign out')),
          ),
        ]),
      ),
    );
  }
}
