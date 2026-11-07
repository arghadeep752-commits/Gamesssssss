import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../services/notifications.dart';
import '../../services/session.dart';
import '../calls/call_controller.dart';
import '../calls/call_screens.dart';

class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key, required this.shell});
  final StatefulNavigationShell shell;

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell> {
  StreamSubscription<Map<String, dynamic>>? _statusSub;

  /// Dot on the Updates tab when a contact posts while you're elsewhere.
  final _newStatus = ValueNotifier<bool>(false);

  @override
  void initState() {
    super.initState();
    final core = ref.read(coreProvider);
    _statusSub = core.realtime.statuses.listen((e) {
      if (e['op'] == 'insert' && e['user_id'] != core.userId && widget.shell.currentIndex != 1) {
        _newStatus.value = true;
      }
    });
    core.calls.presentCallScreen = () {
      if (!mounted || CallScreen.isOpen) return;
      GoRouter.of(context).push('/call');
    };
    NotificationService.instance.pendingRoute.addListener(_openPending);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _openPending();
      core.calls.checkIncoming();
    });
  }

  void _openPending() {
    final route = NotificationService.instance.pendingRoute.value;
    if (route == null || !mounted) return;
    NotificationService.instance.pendingRoute.value = null;
    if (route == '/calls') {
      widget.shell.goBranch(3);
    } else if (route == '/call') {
      ref.read(coreProvider).calls.checkIncoming();
    } else {
      GoRouter.of(context).push(route);
    }
  }

  @override
  void dispose() {
    _statusSub?.cancel();
    _newStatus.dispose();
    NotificationService.instance.pendingRoute.removeListener(_openPending);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final core = ref.watch(coreProvider);
    return Scaffold(
      body: Column(children: [
        Expanded(child: widget.shell),
        ListenableBuilder(
          listenable: core.calls,
          builder: (context, _) {
            final c = core.calls;
            if (!c.inCall || c.phase == CallPhase.incoming) return const SizedBox.shrink();
            return Material(
              color: HimeColors.online,
              child: InkWell(
                onTap: () => GoRouter.of(context).push('/call'),
                child: SafeArea(
                  top: false,
                  bottom: false,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
                    child: Row(children: [
                      Icon(c.video ? Icons.videocam_rounded : Icons.call_rounded, color: Colors.white, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text('Tap to return to call · ${c.peerName}',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                      ),
                    ]),
                  ),
                ),
              ),
            );
          },
        ),
      ]),
      bottomNavigationBar: ListenableBuilder(
        listenable: Listenable.merge([core.chatList, _newStatus]),
        builder: (context, _) => _HimeNavBar(
          index: widget.shell.currentIndex,
          unreadChats: core.chatList.unreadChats,
          newStatus: _newStatus.value && widget.shell.currentIndex != 1,
          onTap: (i) {
            if (i == 1) _newStatus.value = false;
            widget.shell.goBranch(i, initialLocation: i == widget.shell.currentIndex);
          },
        ),
      ),
    );
  }
}

class _HimeNavBar extends StatelessWidget {
  const _HimeNavBar({required this.index, required this.onTap, required this.unreadChats, this.newStatus = false});
  final int index;
  final ValueChanged<int> onTap;
  final int unreadChats;
  final bool newStatus;

  static const _items = [
    (Icons.chat_bubble_outline_rounded, Icons.chat_bubble_rounded, 'Chats'),
    (Icons.blur_circular_outlined, Icons.blur_circular_rounded, 'Updates'),
    (Icons.groups_outlined, Icons.groups_rounded, 'Communities'),
    (Icons.call_outlined, Icons.call_rounded, 'Calls'),
    (Icons.settings_outlined, Icons.settings_rounded, 'Settings'),
  ];

  @override
  Widget build(BuildContext context) {
    // The bar's colour also fills the area behind the (transparent) system
    // navigation bar, so the bottom of the screen looks like one piece.
    return MediaQuery.withClampedTextScaling(
      maxScaleFactor: 1.2,
      child: Container(
      decoration: BoxDecoration(
        color: context.colors.surface,
        border: Border(top: BorderSide(color: context.palette.border)),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 66,
          child: Row(children: [
            for (var i = 0; i < _items.length; i++)
              Expanded(
                child: InkResponse(
                  onTap: () => onTap(i),
                  radius: 36,
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    Stack(clipBehavior: Clip.none, children: [
                      AnimatedContainer(
                        duration: const Duration(milliseconds: 220),
                        curve: Curves.easeOutCubic,
                        width: i == index ? 56 : 36,
                        height: 30,
                        decoration: BoxDecoration(
                          color: i == index ? HimeColors.yellow : Colors.transparent,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Icon(i == index ? _items[i].$2 : _items[i].$1,
                            size: 22, color: i == index ? HimeColors.ink : context.palette.muted),
                      ),
                      if (i == 0 && unreadChats > 0)
                        Positioned(
                          right: -4,
                          top: -4,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                            decoration: BoxDecoration(
                              color: HimeColors.ink,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: context.colors.surface, width: 1.5),
                            ),
                            child: Text('$unreadChats',
                                style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w700)),
                          ),
                        ),
                      if (i == 1 && newStatus)
                        Positioned(
                          right: -1,
                          top: -1,
                          child: Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              color: HimeColors.online,
                              shape: BoxShape.circle,
                              border: Border.all(color: context.colors.surface, width: 1.5),
                            ),
                          ),
                        ),
                    ]),
                    const SizedBox(height: 4),
                    // One line always ("Communities" used to wrap on narrow
                    // phones or with large system fonts).
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 2),
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          _items[i].$3,
                          maxLines: 1,
                          softWrap: false,
                          style: TextStyle(
                            fontSize: 11.5,
                            fontWeight: i == index ? FontWeight.w700 : FontWeight.w500,
                            color: i == index ? context.colors.onSurface : context.palette.muted,
                          ),
                        ),
                      ),
                    ),
                  ]),
                ),
              ),
          ]),
        ),
      ),
      ),
    );
  }
}
