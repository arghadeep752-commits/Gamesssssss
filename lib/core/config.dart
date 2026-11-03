import 'dart:convert';

import 'package:flutter/services.dart';

/// Runtime configuration. Values come from `assets/config/hime.json` and can
/// be overridden at build time with `--dart-define` (see docs/SETUP.md).
/// Only publishable values live here: never a service-role or secret key.
class AppConfig {
  AppConfig({
    required this.supabaseUrl,
    required this.supabaseKey,
    required this.authRedirectUrl,
    required this.inviteBaseUrl,
    this.firebase,
  });

  final String supabaseUrl;
  final String supabaseKey;
  final String authRedirectUrl;
  final String inviteBaseUrl;

  /// Firebase options for push notifications (apiKey, appId,
  /// messagingSenderId, projectId). Null until Firebase is configured.
  final Map<String, String>? firebase;

  static late AppConfig instance;

  bool get pushConfigured => firebase != null;

  static Future<AppConfig> load() async {
    Map<String, dynamic> file = {};
    try {
      file = jsonDecode(await rootBundle.loadString('assets/config/hime.json'))
          as Map<String, dynamic>;
    } catch (_) {}
    const urlOverride = String.fromEnvironment('HIME_SUPABASE_URL');
    const keyOverride = String.fromEnvironment('HIME_SUPABASE_KEY');
    const fbOverride = String.fromEnvironment('HIME_FIREBASE_JSON');
    Map<String, String>? firebase;
    final rawFirebase = fbOverride.isNotEmpty ? jsonDecode(fbOverride) : file['firebase'];
    if (rawFirebase is Map && rawFirebase['apiKey'] != null) {
      firebase = rawFirebase.map((k, v) => MapEntry('$k', '$v'));
    }
    instance = AppConfig(
      supabaseUrl: urlOverride.isNotEmpty ? urlOverride : (file['supabaseUrl'] as String? ?? ''),
      supabaseKey: keyOverride.isNotEmpty ? keyOverride : (file['supabasePublishableKey'] as String? ?? ''),
      authRedirectUrl: file['authRedirectUrl'] as String? ?? 'app.hime://auth-callback',
      inviteBaseUrl: file['inviteBaseUrl'] as String? ?? 'app.hime://join',
      firebase: firebase,
    );
    return instance;
  }
}
