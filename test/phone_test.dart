import 'package:flutter_test/flutter_test.dart';
import 'package:hime/core/utils.dart';

void main() {
  test('phone numbers are shown readably', () {
    expect(prettyPhone('+919876543210'), '+91 98765 43210');
    expect(prettyPhone('919876543210'), '+91 98765 43210');
    expect(prettyPhone('+14155550123'), '+14155550123');
  });

  test('phone-only placeholder addresses are recognised', () {
    expect(isPlaceholderEmail('p919876543210-a1b2c3@phone.hime.invalid'), isTrue);
    expect(isPlaceholderEmail('someone@gmail.com'), isFalse);
    expect(isPlaceholderEmail(null), isFalse);
  });

  test('numbers typed with spaces or a leading 0 become E.164', () {
    expect(Phone.toE164('98765 43210', '+91'), '+919876543210');
    expect(Phone.toE164('098765 43210', '+91'), '+919876543210');
    expect(Phone.toE164('+91 98765 43210', '+91'), '+919876543210');
  });
}
