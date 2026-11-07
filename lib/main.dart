import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'app.dart';
import 'core/config.dart';
import 'core/theme.dart';
import 'services/notifications.dart';
import 'services/secure_store.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Draw behind transparent status and navigation bars (full-screen look).
  await SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(HimeSystemUi.of(
      dark: WidgetsBinding.instance.platformDispatcher.platformBrightness == Brightness.dark));
  final config = await AppConfig.load();
  final prefs = await SharedPreferences.getInstance();
  await Supabase.initialize(
    url: config.supabaseUrl,
    publishableKey: config.supabaseKey,
    authOptions: const FlutterAuthClientOptions(
      authFlowType: AuthFlowType.pkce,
      localStorage: SecureSessionStorage(),
    ),
    realtimeClientOptions: const RealtimeClientOptions(eventsPerSecond: 20),
    debug: false,
  );
  try {
    await NotificationService.instance.init();
  } catch (e) {
    debugPrint('Notifications unavailable: $e');
  }
  PlatformDispatcher.instance.onError = (error, stack) {
    debugPrint('Uncaught: $error');
    return true;
  };
  runApp(ProviderScope(
    overrides: [sharedPrefsProvider.overrideWithValue(prefs)],
    child: const HimeApp(),
  ));
}
