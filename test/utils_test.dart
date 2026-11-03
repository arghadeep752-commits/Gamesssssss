import 'package:flutter_test/flutter_test.dart';
import 'package:hime/core/utils.dart';
import 'package:hime/features/chats/models.dart';

void main() {
  group('Phone', () {
    test('normalises Indian numbers to E.164', () {
      expect(Phone.toE164('98765 43210', '+91'), '+919876543210');
      expect(Phone.toE164('098765-43210', '+91'), '+919876543210');
      expect(Phone.toE164('+91 98765 43210', '+91'), '+919876543210');
      expect(Phone.toE164('0091 98765 43210', '+91'), '+919876543210');
      expect(Phone.toE164('919876543210', '+91'), '+919876543210');
    });

    test('rejects junk', () {
      expect(Phone.toE164('', '+91'), isNull);
      expect(Phone.toE164('123', '+91'), isNull);
    });

    test('hash is stable and format independent', () {
      expect(Phone.hash('+919876543210'), Phone.hash('+91 98765 43210'));
      expect(Phone.hash('+919876543210'), hasLength(64));
    });
  });

  group('Fmt', () {
    test('duration', () {
      expect(Fmt.duration(const Duration(seconds: 5)), '00:05');
      expect(Fmt.duration(const Duration(minutes: 3, seconds: 7)), '03:07');
      expect(Fmt.duration(const Duration(hours: 1, minutes: 2, seconds: 3)), '1:02:03');
    });

    test('bytes', () {
      expect(Fmt.bytes(512), '512 B');
      expect(Fmt.bytes(2048), '2 KB');
      expect(Fmt.bytes(5 * 1024 * 1024), '5.0 MB');
    });

    test('initials', () {
      expect(Fmt.initials('Priya Sharma'), 'PS');
      expect(Fmt.initials('arjun'), 'A');
      expect(Fmt.initials('  '), '?');
    });

    test('last seen', () {
      expect(Fmt.lastSeen(null), '');
      expect(Fmt.lastSeen(DateTime.now().subtract(const Duration(seconds: 10))), 'last seen just now');
      expect(Fmt.lastSeen(DateTime.now().subtract(const Duration(minutes: 5))), 'last seen 5 min ago');
    });
  });

  group('Validators', () {
    test('email', () {
      expect(Validators.email('a@b.in'), isNull);
      expect(Validators.email('nope'), isNotNull);
    });
    test('password', () {
      expect(Validators.password('short1'), isNotNull);
      expect(Validators.password('longenough'), isNotNull);
      expect(Validators.password('longenough1'), isNull);
    });
    test('username', () {
      expect(Validators.username('hime_user'), isNull);
      expect(Validators.username('ab'), isNotNull);
      expect(Validators.username('bad name'), isNotNull);
    });
  });

  test('findUrls', () {
    expect(findUrls('see https://hime.app/x and www.example.com now'), ['https://hime.app/x', 'www.example.com']);
    expect(findUrls('no links here'), isEmpty);
  });

  group('message previews', () {
    test('media kinds', () {
      expect(ChatMessage.previewFor('image', {}), '📷 Photo');
      expect(ChatMessage.previewFor('image', {'text': 'Goa!'}), '📷 Goa!');
      expect(ChatMessage.previewFor('voice', {}), '🎤 Voice message');
      expect(ChatMessage.previewFor('document', {'media': {'name': 'ticket.pdf'}}), '📄 ticket.pdf');
      expect(ChatMessage.previewFor('text', {'text': 'hello'}), 'hello');
    });

    test('call labels', () {
      expect(ChatMessage.callLabel({'media': 'audio', 'status': 'missed'}), '📞 Missed voice call');
      expect(ChatMessage.callLabel({'media': 'video', 'status': 'ended', 'duration': 65}), '🎥 Video call · 01:05');
    });

    test('system labels', () {
      String names(String? id) => id == 'u1' ? 'Asha' : 'Ravi';
      expect(ChatMessage.systemLabel({'type': 'group_created', 'actor': 'u1', 'name': 'Family'}, names), 'Asha created the group "Family"');
      expect(ChatMessage.systemLabel({'type': 'members_added', 'actor': 'u1', 'targets': ['u2']}, names), 'Asha added Ravi');
    });
  });
}
