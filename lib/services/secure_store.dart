import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Android Keystore–backed storage for secrets: the auth session, the
/// device's private identity key and the local database key.
class SecureStore {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static Future<String?> read(String key) async {
    try {
      return await _storage.read(key: key);
    } catch (_) {
      return null;
    }
  }

  static Future<void> write(String key, String value) => _storage.write(key: key, value: value);

  static Future<void> delete(String key) => _storage.delete(key: key);
}

/// Persists the Supabase session in the Keystore instead of plain prefs.
class SecureSessionStorage extends LocalStorage {
  const SecureSessionStorage();
  static const _key = 'hime.session';

  @override
  Future<void> initialize() async {}

  @override
  Future<bool> hasAccessToken() async => (await SecureStore.read(_key)) != null;

  @override
  Future<String?> accessToken() => SecureStore.read(_key);

  @override
  Future<void> persistSession(String persistSessionString) => SecureStore.write(_key, persistSessionString);

  @override
  Future<void> removePersistedSession() => SecureStore.delete(_key);
}
