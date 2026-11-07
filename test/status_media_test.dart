import 'package:flutter_test/flutter_test.dart';
import 'package:hime/features/updates/updates.dart';

void main() {
  group('sniffMediaType', () {
    test('recognises photos by their first bytes', () {
      expect(sniffMediaType([0xFF, 0xD8, 0xFF, 0xE0, 0, 0], video: false)?.mime, 'image/jpeg');
      expect(sniffMediaType([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A], video: false)?.ext, 'png');
      expect(
        sniffMediaType([0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50], video: false)?.mime,
        'image/webp',
      );
      // GIF and HEIC are not accepted by the status bucket.
      expect(sniffMediaType('GIF89a'.codeUnits, video: false), isNull);
    });

    test('recognises videos by their container', () {
      List<int> ftyp(String brand) => [0, 0, 0, 0x18, ...'ftyp'.codeUnits, ...brand.codeUnits];
      expect(sniffMediaType(ftyp('isom'), video: true)?.mime, 'video/mp4');
      expect(sniffMediaType(ftyp('mp42'), video: true)?.ext, 'mp4');
      expect(sniffMediaType(ftyp('qt  '), video: true)?.mime, 'video/quicktime');
      expect(sniffMediaType(ftyp('3gp4'), video: true)?.mime, 'video/3gpp');
      expect(sniffMediaType([0x1A, 0x45, 0xDF, 0xA3, 0, 0], video: true)?.mime, 'video/webm');
      expect(sniffMediaType([1, 2, 3, 4, 5, 6, 7, 8], video: true), isNull);
    });
  });
}
