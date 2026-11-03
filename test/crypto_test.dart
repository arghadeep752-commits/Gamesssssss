import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hime/services/e2ee.dart';

void main() {
  group('E2ee message envelopes', () {
    late E2ee alice;
    late E2ee bobPhone;
    late E2ee bobTablet;
    late E2ee eve;

    setUp(() async {
      alice = await E2ee.inMemory('alice-phone');
      bobPhone = await E2ee.inMemory('bob-phone');
      bobTablet = await E2ee.inMemory('bob-tablet');
      eve = await E2ee.inMemory('eve-phone');
    });

    Future<Sealed> seal(Map<String, dynamic> payload) => alice.seal(
          payload: payload,
          messageId: 'm-1',
          conversationId: 'c-1',
          senderId: 'alice',
          recipients: {
            'alice-phone': alice.publicKeyB64,
            'bob-phone': bobPhone.publicKeyB64,
            'bob-tablet': bobTablet.publicKeyB64,
          },
        );

    Future<Map<String, dynamic>> open(E2ee who, Sealed s, String device,
            {String messageId = 'm-1', String conversationId = 'c-1', String? senderKey, String? ciphertext}) =>
        who.open(
          ciphertext: ciphertext ?? s.ciphertext,
          nonce: s.nonce,
          ephKey: s.ephKey,
          wrappedKey: s.keys[device]!,
          senderPublicKey: senderKey ?? alice.publicKeyB64,
          messageId: messageId,
          conversationId: conversationId,
          senderId: 'alice',
          senderDeviceId: 'alice-phone',
        );

    test('every recipient device can decrypt', () async {
      final s = await seal({'t': 'text', 'text': 'Namaste 🙏 — Hime'});
      expect(s.keys.keys, containsAll(['alice-phone', 'bob-phone', 'bob-tablet']));
      for (final (who, device) in [(alice, 'alice-phone'), (bobPhone, 'bob-phone'), (bobTablet, 'bob-tablet')]) {
        final out = await open(who, s, device);
        expect(out['text'], 'Namaste 🙏 — Hime');
      }
    });

    test('ciphertext does not contain the plaintext', () async {
      final s = await seal({'t': 'text', 'text': 'secret meeting at 5'});
      expect(s.ciphertext.contains('secret'), isFalse);
    });

    test('a non-recipient cannot unwrap the key', () async {
      final s = await seal({'t': 'text', 'text': 'hi'});
      await expectLater(open(eve, s, 'bob-phone'), throwsA(anything));
    });

    test('moving a message to another conversation or id fails', () async {
      final s = await seal({'t': 'text', 'text': 'hi'});
      await expectLater(open(bobPhone, s, 'bob-phone', conversationId: 'c-2'), throwsA(anything));
      await expectLater(open(bobPhone, s, 'bob-phone', messageId: 'm-2'), throwsA(anything));
    });

    test('forged sender identity fails', () async {
      final s = await seal({'t': 'text', 'text': 'hi'});
      await expectLater(open(bobPhone, s, 'bob-phone', senderKey: eve.publicKeyB64), throwsA(anything));
    });

    test('tampered ciphertext fails', () async {
      final s = await seal({'t': 'text', 'text': 'pay 100'});
      final chars = s.ciphertext.split('');
      chars[2] = chars[2] == 'A' ? 'B' : 'A';
      await expectLater(open(bobPhone, s, 'bob-phone', ciphertext: chars.join()), throwsA(anything));
    });

    test('safety numbers match on both sides and change with keys', () {
      final a = E2ee.safetyNumber('alice', [alice.publicKeyB64], 'bob', [bobPhone.publicKeyB64, bobTablet.publicKeyB64]);
      final b = E2ee.safetyNumber('bob', [bobTablet.publicKeyB64, bobPhone.publicKeyB64], 'alice', [alice.publicKeyB64]);
      expect(a, b);
      final c = E2ee.safetyNumber('alice', [alice.publicKeyB64], 'bob', [bobPhone.publicKeyB64]);
      expect(c, isNot(a));
      expect(a.replaceAll(RegExp(r'\s'), '').length, 60);
    });
  });

  group('MediaCrypto', () {
    late Directory dir;
    setUp(() async => dir = await Directory.systemTemp.createTemp('hime_media_test'));
    tearDown(() async => dir.delete(recursive: true));

    for (final size in [0, 1, MediaCrypto.chunk - 1, MediaCrypto.chunk, MediaCrypto.chunk * 3 + 17]) {
      test('round trip of $size bytes', () async {
        final input = File('${dir.path}/in')..writeAsBytesSync(MediaCrypto.randomBytes(size));
        final enc = File('${dir.path}/enc');
        final out = File('${dir.path}/out');
        final key = MediaCrypto.randomBytes(32);
        final nonce = MediaCrypto.randomBytes(12);
        await MediaCrypto.encryptFile(input, enc, key, nonce);
        await MediaCrypto.decryptFile(enc, out, key, nonce);
        expect(out.readAsBytesSync(), input.readAsBytesSync());
      });
    }

    test('truncation is detected', () async {
      final input = File('${dir.path}/in')..writeAsBytesSync(MediaCrypto.randomBytes(MediaCrypto.chunk * 2 + 5));
      final enc = File('${dir.path}/enc');
      final key = MediaCrypto.randomBytes(32);
      final nonce = MediaCrypto.randomBytes(12);
      await MediaCrypto.encryptFile(input, enc, key, nonce);
      final bytes = enc.readAsBytesSync();
      final cut = File('${dir.path}/cut')..writeAsBytesSync(bytes.sublist(0, MediaCrypto.chunk + 16));
      await expectLater(MediaCrypto.decryptFile(cut, File('${dir.path}/out'), key, nonce), throwsA(anything));
    });

    test('wrong key is rejected', () async {
      final input = File('${dir.path}/in')..writeAsBytesSync(MediaCrypto.randomBytes(1000));
      final enc = File('${dir.path}/enc');
      final nonce = MediaCrypto.randomBytes(12);
      await MediaCrypto.encryptFile(input, enc, MediaCrypto.randomBytes(32), nonce);
      await expectLater(MediaCrypto.decryptFile(enc, File('${dir.path}/out'), MediaCrypto.randomBytes(32), nonce), throwsA(anything));
    });
  });
}
