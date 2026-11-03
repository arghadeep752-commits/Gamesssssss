import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:crypto/crypto.dart' as crypto;
import 'package:cryptography/cryptography.dart';

import 'secure_store.dart';

/// End-to-end encryption for Hime messages and media.
///
/// Every installation owns an X25519 identity key pair; the private half
/// never leaves the Keystore-backed secure storage. A message is encrypted
/// once with a random 256-bit content key (ChaCha20-Poly1305, bound to the
/// conversation, message id and sender device as associated data). The
/// content key is then wrapped for every recipient device with a key derived
/// (HKDF-SHA256) from two X25519 agreements — ephemeral→recipient and
/// sender identity→recipient — so only the recipient can unwrap it and the
/// recipient can tell the sender's device produced it. This mirrors HPKE's
/// authenticated mode using only audited primitives from package:cryptography.
/// It does not provide the per-message forward secrecy of Signal's double
/// ratchet; see docs/SECURITY.md.
class E2ee {
  E2ee._(this._identity, this.publicKey, this.deviceId);

  static final _x25519 = X25519();
  static final _aead = Chacha20.poly1305Aead();
  static final _hkdf = Hkdf(hmac: Hmac.sha256(), outputLength: 32);
  static const _wrapInfo = 'hime/v1/wrap';

  final SimpleKeyPairData _identity;
  final List<int> publicKey;
  String deviceId;

  String get publicKeyB64 => base64Encode(publicKey);

  /// Loads this install's identity key for [userId], creating it on first use.
  static Future<E2ee> load(String userId) async {
    final storeKey = 'hime.identity.$userId';
    final stored = await SecureStore.read(storeKey);
    if (stored != null) {
      final parts = stored.split(':');
      final priv = base64Decode(parts[0]);
      final pub = base64Decode(parts[1]);
      final kp = SimpleKeyPairData(priv, publicKey: SimplePublicKey(pub, type: KeyPairType.x25519), type: KeyPairType.x25519);
      return E2ee._(kp, pub, parts.length > 2 ? parts[2] : '');
    }
    final kp = await _x25519.newKeyPair();
    final data = await kp.extract();
    final priv = await data.extractPrivateKeyBytes();
    final pub = data.publicKey.bytes;
    await SecureStore.write(storeKey, '${base64Encode(priv)}:${base64Encode(pub)}');
    return E2ee._(data, pub, '');
  }

  /// Creates an identity that lives only in memory (tests and tooling).
  static Future<E2ee> inMemory([String deviceId = '']) async {
    final kp = await _x25519.newKeyPair();
    final data = await kp.extract();
    return E2ee._(data, data.publicKey.bytes, deviceId);
  }

  /// Remembers the server-assigned device id next to the key.
  static Future<void> saveDeviceId(String userId, E2ee e2ee, String deviceId) async {
    final storeKey = 'hime.identity.$userId';
    final priv = await e2ee._identity.extractPrivateKeyBytes();
    await SecureStore.write(storeKey, '${base64Encode(priv)}:${base64Encode(e2ee.publicKey)}:$deviceId');
    e2ee.deviceId = deviceId;
  }

  static Future<void> forget(String userId) => SecureStore.delete('hime.identity.$userId');

  static List<int> _aad(String conversationId, String messageId, String senderId, String senderDeviceId) =>
      utf8.encode('hime/v1|$conversationId|$messageId|$senderId|$senderDeviceId');

  Future<SecretKey> _kek(List<int> dh1, List<int> dh2, List<int> ephPub, List<int> senderPub, List<int> recipientPub) {
    return _hkdf.deriveKey(
      secretKey: SecretKey([...dh1, ...dh2]),
      nonce: [...ephPub, ...senderPub, ...recipientPub],
      info: utf8.encode(_wrapInfo),
    );
  }

  Future<List<int>> _dh(KeyPair kp, List<int> remote) async {
    final shared = await _x25519.sharedSecretKey(
      keyPair: kp,
      remotePublicKey: SimplePublicKey(remote, type: KeyPairType.x25519),
    );
    return shared.extractBytes();
  }

  /// Encrypts [payload] for [recipients] (device id → base64 public key).
  Future<Sealed> seal({
    required Map<String, dynamic> payload,
    required String messageId,
    required String conversationId,
    required String senderId,
    required Map<String, String> recipients,
  }) async {
    final contentKey = SecretKeyData.random(length: 32);
    final box = await _aead.encrypt(
      utf8.encode(jsonEncode(payload)),
      secretKey: contentKey,
      aad: _aad(conversationId, messageId, senderId, deviceId),
    );
    final eph = await _x25519.newKeyPair();
    final ephPub = (await eph.extractPublicKey()).bytes;
    final keyBytes = await contentKey.extractBytes();
    final keys = <String, String>{};
    for (final r in recipients.entries) {
      final recipientPub = base64Decode(r.value);
      final dh1 = await _dh(eph, recipientPub);
      final dh2 = await _dh(_identity, recipientPub);
      final kek = await _kek(dh1, dh2, ephPub, publicKey, recipientPub);
      final wrapped = await _aead.encrypt(keyBytes, secretKey: kek, aad: utf8.encode('$messageId|${r.key}'));
      keys[r.key] = base64Encode(wrapped.concatenation());
    }
    return Sealed(
      ciphertext: base64Encode([...box.cipherText, ...box.mac.bytes]),
      nonce: base64Encode(box.nonce),
      ephKey: base64Encode(ephPub),
      keys: keys,
    );
  }

  /// Decrypts a message envelope addressed to this device.
  Future<Map<String, dynamic>> open({
    required String ciphertext,
    required String nonce,
    required String ephKey,
    required String wrappedKey,
    required String senderPublicKey,
    required String messageId,
    required String conversationId,
    required String senderId,
    required String senderDeviceId,
  }) async {
    final ephPub = base64Decode(ephKey);
    final senderPub = base64Decode(senderPublicKey);
    final dh1 = await _dh(_identity, ephPub);
    final dh2 = await _dh(_identity, senderPub);
    final kek = await _kek(dh1, dh2, ephPub, senderPub, publicKey);
    final wrap = SecretBox.fromConcatenation(base64Decode(wrappedKey), nonceLength: 12, macLength: 16);
    final keyBytes = await _aead.decrypt(wrap, secretKey: kek, aad: utf8.encode('$messageId|$deviceId'));
    final data = base64Decode(ciphertext);
    final box = SecretBox(
      data.sublist(0, data.length - 16),
      nonce: base64Decode(nonce),
      mac: Mac(data.sublist(data.length - 16)),
    );
    final clear = await _aead.decrypt(
      box,
      secretKey: SecretKey(keyBytes),
      aad: _aad(conversationId, messageId, senderId, senderDeviceId),
    );
    return jsonDecode(utf8.decode(clear)) as Map<String, dynamic>;
  }

  /// Comparable security code for two people (same on both phones).
  static String safetyNumber(String userA, List<String> keysA, String userB, List<String> keysB) {
    String side(String u, List<String> k) => '$u:${(List.of(k)..sort()).join(',')}';
    final parts = [side(userA, keysA), side(userB, keysB)]..sort();
    final digest = crypto.sha512.convert(utf8.encode(parts.join('|'))).bytes;
    final buf = StringBuffer();
    for (var i = 0; i < 12; i++) {
      final v = ((digest[i * 3] << 16) | (digest[i * 3 + 1] << 8) | digest[i * 3 + 2]) % 100000;
      buf.write(v.toString().padLeft(5, '0'));
      if (i != 11) buf.write(i % 4 == 3 ? '\n' : ' ');
    }
    return buf.toString();
  }
}

class Sealed {
  Sealed({required this.ciphertext, required this.nonce, required this.ephKey, required this.keys});
  final String ciphertext;
  final String nonce;
  final String ephKey;
  final Map<String, String> keys;
}

/// Symmetric encryption for data at rest on this phone (local message cache).
class LocalVault {
  LocalVault._(this._key);
  final SecretKey _key;
  static final _aead = Chacha20.poly1305Aead();

  static Future<LocalVault> load(String userId) async {
    final storeKey = 'hime.vault.$userId';
    var b64 = await SecureStore.read(storeKey);
    if (b64 == null) {
      final key = SecretKeyData.random(length: 32);
      b64 = base64Encode(await key.extractBytes());
      await SecureStore.write(storeKey, b64);
    }
    return LocalVault._(SecretKey(base64Decode(b64)));
  }

  Future<Uint8List> seal(String clear) async {
    final box = await _aead.encrypt(utf8.encode(clear), secretKey: _key);
    return box.concatenation();
  }

  Future<String> open(List<int> data) async {
    final box = SecretBox.fromConcatenation(data, nonceLength: 12, macLength: 16);
    return utf8.decode(await _aead.decrypt(box, secretKey: _key));
  }
}

/// Chunked authenticated encryption for media files (STREAM construction:
/// per-chunk nonce from a base nonce and counter; the last chunk is flagged
/// so truncation is detected). Works in 64 KB pieces to keep memory low.
class MediaCrypto {
  static const chunk = 64 * 1024;
  static const _mac = 16;
  static final _aead = Chacha20.poly1305Aead();

  static List<int> randomBytes(int n) {
    final r = Random.secure();
    return List<int>.generate(n, (_) => r.nextInt(256));
  }

  static List<int> _nonce(List<int> base, int index) {
    final n = List<int>.of(base);
    n[8] ^= (index >> 24) & 0xff;
    n[9] ^= (index >> 16) & 0xff;
    n[10] ^= (index >> 8) & 0xff;
    n[11] ^= index & 0xff;
    return n;
  }

  /// Encrypts [input] into [output]; returns the encrypted length.
  static Future<int> encryptFile(File input, File output, List<int> key, List<int> baseNonce,
      {void Function(double)? onProgress}) async {
    final total = await input.length();
    final count = max(1, (total / chunk).ceil());
    final reader = await input.open();
    final sink = output.openWrite();
    final secret = SecretKey(key);
    var written = 0;
    try {
      for (var i = 0; i < count; i++) {
        final data = await reader.read(chunk);
        final box = await _aead.encrypt(data, secretKey: secret, nonce: _nonce(baseNonce, i), aad: [i == count - 1 ? 1 : 0]);
        sink.add(box.cipherText);
        sink.add(box.mac.bytes);
        written += box.cipherText.length + _mac;
        onProgress?.call((i + 1) / count);
      }
    } finally {
      await reader.close();
      await sink.flush();
      await sink.close();
    }
    return written;
  }

  static Future<void> decryptFile(File input, File output, List<int> key, List<int> baseNonce,
      {void Function(double)? onProgress}) async {
    final total = await input.length();
    final count = max(1, (total / (chunk + _mac)).ceil());
    final reader = await input.open();
    final sink = output.openWrite();
    final secret = SecretKey(key);
    try {
      for (var i = 0; i < count; i++) {
        final data = await reader.read(chunk + _mac);
        if (data.length < _mac) throw const FormatException('Truncated media');
        final box = SecretBox(
          data.sublist(0, data.length - _mac),
          nonce: _nonce(baseNonce, i),
          mac: Mac(data.sublist(data.length - _mac)),
        );
        sink.add(await _aead.decrypt(box, secretKey: secret, aad: [i == count - 1 ? 1 : 0]));
        onProgress?.call((i + 1) / count);
      }
    } finally {
      await reader.close();
      await sink.flush();
      await sink.close();
    }
  }
}
