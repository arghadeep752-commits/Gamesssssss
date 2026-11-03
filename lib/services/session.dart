import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../core/widgets.dart';
import 'core.dart';
import 'notifications.dart';

enum SessionStage { loading, signedOut, needsMfa, recovery, needsOnboarding, ready, error }

/// The signed-in user's own profile row.
class MyProfile {
  MyProfile(this.data);
  final Map<String, dynamic> data;
  String get id => data['id'] as String;
  String get displayName => (data['display_name'] as String?) ?? '';
  String? get username => data['username'] as String?;
  String get about => (data['about'] as String?) ?? '';
  String? get avatarPath => data['avatar_path'] as String?;
  int get avatarVersion => (data['avatar_version'] as num?)?.toInt() ?? 0;
  bool get onboarded => data['onboarded'] == true;
  String get name => displayName.isNotEmpty ? displayName : (username ?? 'You');
}

/// Drives routing: which part of the app the user may see right now, and
/// owns the per-account [HimeCore] while signed in.
class SessionController extends ChangeNotifier {
  SessionController() {
    _authSub = _sb.auth.onAuthStateChange.listen(_onAuth, onError: (_) {});
    unawaited(_evaluate());
  }

  SupabaseClient get _sb => Supabase.instance.client;
  StreamSubscription<AuthState>? _authSub;

  SessionStage stage = SessionStage.loading;
  HimeCore? core;
  MyProfile? profile;
  Object? error;
  bool _evaluating = false;
  bool _again = false;
  CoreLifecycle? _lifecycle;

  User? get user => _sb.auth.currentUser;

  void _onAuth(AuthState s) {
    switch (s.event) {
      case AuthChangeEvent.passwordRecovery:
        stage = SessionStage.recovery;
        notifyListeners();
      case AuthChangeEvent.signedOut:
        unawaited(_teardown().then((_) {
          stage = SessionStage.signedOut;
          notifyListeners();
        }));
      case AuthChangeEvent.signedIn:
      case AuthChangeEvent.initialSession:
      case AuthChangeEvent.mfaChallengeVerified:
      case AuthChangeEvent.userUpdated:
        if (stage != SessionStage.recovery) unawaited(_evaluate());
      default:
        break;
    }
  }

  /// Re-checks session, MFA level and onboarding, then starts the core.
  Future<void> _evaluate() async {
    if (_evaluating) {
      _again = true;
      return;
    }
    _evaluating = true;
    try {
      do {
        _again = false;
        final session = _sb.auth.currentSession;
        if (session == null) {
          await _teardown();
          stage = SessionStage.signedOut;
          notifyListeners();
          continue;
        }
        final aal = _sb.auth.mfa.getAuthenticatorAssuranceLevel();
        if (aal.nextLevel == AuthenticatorAssuranceLevels.aal2 && aal.currentLevel != AuthenticatorAssuranceLevels.aal2) {
          stage = SessionStage.needsMfa;
          notifyListeners();
          continue;
        }
        await refreshProfile();
        if (profile == null || !profile!.onboarded) {
          stage = SessionStage.needsOnboarding;
          notifyListeners();
          continue;
        }
        if (core == null || core!.userId != session.user.id) {
          await _teardown();
          final c = await HimeCore.create(_sb, session.user.id);
          core = c;
          _lifecycle = CoreLifecycle(c)..attach();
          await c.start();
          unawaited(NotificationService.instance.requestPermission());
        }
        error = null;
        stage = SessionStage.ready;
        notifyListeners();
      } while (_again);
    } catch (e) {
      debugPrint('session evaluate failed: $e');
      error = e;
      if (core == null) {
        stage = SessionStage.error;
        notifyListeners();
      }
    } finally {
      _evaluating = false;
    }
  }

  Future<void> retry() => _evaluate();

  Future<void> refreshProfile() async {
    final uid = _sb.auth.currentUser?.id;
    if (uid == null) return;
    final row = await _sb.from('profiles').select().eq('id', uid).maybeSingle();
    profile = row == null ? null : MyProfile(row);
    notifyListeners();
  }

  /// Called after onboarding / MFA so routing moves on.
  Future<void> continueAfterSetup() => _evaluate();

  Future<void> finishRecovery() async {
    stage = SessionStage.loading;
    notifyListeners();
    await _evaluate();
  }

  Future<void> signOut({bool everywhere = false}) async {
    final c = core;
    try {
      await NotificationService.instance.unregisterPush();
      if (c != null) {
        await c.sb.from('user_devices').delete().eq('id', c.deviceId);
      }
    } catch (_) {}
    await _sb.auth.signOut(scope: everywhere ? SignOutScope.global : SignOutScope.local);
  }

  Future<void> _teardown() async {
    final c = core;
    core = null;
    _lifecycle?.detach();
    _lifecycle = null;
    SignedUrls.clear();
    if (c != null) {
      try {
        await c.dispose();
      } catch (_) {}
    }
  }

  @override
  void dispose() {
    _authSub?.cancel();
    super.dispose();
  }
}

final sessionProvider = ChangeNotifierProvider<SessionController>((ref) => SessionController());

/// The signed-in core (only valid inside the main app area).
final coreProvider = Provider<HimeCore>((ref) {
  final core = ref.watch(sessionProvider.select((s) => s.core));
  if (core == null) throw StateError('Not signed in');
  return core;
});
