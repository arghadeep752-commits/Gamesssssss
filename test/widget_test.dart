import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hime/core/theme.dart';
import 'package:hime/core/widgets.dart';

Widget _wrap(Widget child) => MaterialApp(theme: HimeTheme.light(), darkTheme: HimeTheme.dark(), home: Scaffold(body: child));

void main() {
  testWidgets('EmptyState shows title, message and action', (tester) async {
    var tapped = false;
    await tester.pumpWidget(_wrap(EmptyState(
      icon: Icons.chat_bubble_outline_rounded,
      title: 'No chats yet',
      message: 'Start a conversation',
      action: TextButton(onPressed: () => tapped = true, child: const Text('New chat')),
    )));
    expect(find.text('No chats yet'), findsOneWidget);
    expect(find.text('Start a conversation'), findsOneWidget);
    await tester.tap(find.text('New chat'));
    expect(tapped, isTrue);
  });

  testWidgets('PrimaryButton shows a spinner while loading', (tester) async {
    await tester.pumpWidget(_wrap(const PrimaryButton(label: 'Continue', loading: true)));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('UnreadBadge caps large counts', (tester) async {
    await tester.pumpWidget(_wrap(const UnreadBadge(count: 1200)));
    expect(find.textContaining('99'), findsOneWidget);
  });

  testWidgets('HimeAvatar falls back to initials', (tester) async {
    await tester.pumpWidget(_wrap(const HimeAvatar(name: 'Meera Nair', size: 48)));
    expect(find.text('MN'), findsOneWidget);
  });

  test('palette is registered for both themes', () {
    expect(HimeTheme.light().extension<HimePalette>(), isNotNull);
    expect(HimeTheme.dark().extension<HimePalette>(), isNotNull);
  });
}
