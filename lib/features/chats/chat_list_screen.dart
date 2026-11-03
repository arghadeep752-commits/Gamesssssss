import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import '../../services/session.dart';
import 'models.dart';

class ChatListScreen extends ConsumerStatefulWidget {
  const ChatListScreen({super.key});

  @override
  ConsumerState<ChatListScreen> createState() => _ChatListScreenState();
}

class _ChatListScreenState extends ConsumerState<ChatListScreen> {
  int _filter = 0;
  Map<String, PresenceInfo> _presence = {};
  Timer? _presenceTimer;

  @override
  void initState() {
    super.initState();
    _presenceTimer = Timer.periodic(const Duration(seconds: 60), (_) => _loadPresence());
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadPresence());
  }

  Future<void> _loadPresence() async {
    final core = ref.read(coreProvider);
    final ids = core.chatList.active.map((c) => c.otherUserId).whereType<String>().take(60).toList();
    final p = await core.presence.lookup(ids);
    if (mounted) setState(() => _presence = p);
  }

  @override
  void dispose() {
    _presenceTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final core = ref.watch(coreProvider);
    final session = ref.watch(sessionProvider);
    final me = session.profile;
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: const HimeLogo(size: 30),
        actions: [
          IconButton(tooltip: 'Search', icon: const Icon(Icons.search_rounded), onPressed: () => context.push('/search')),
          ValueListenableBuilder<bool>(
            valueListenable: core.realtime.connected,
            builder: (_, connected, __) => IconButton(
              tooltip: connected ? 'Connected' : 'Connecting…',
              onPressed: () => context.push('/settings/notifications'),
              icon: Badge(
                isLabelVisible: !connected,
                backgroundColor: HimeColors.yellowDeep,
                smallSize: 8,
                child: const Icon(Icons.notifications_none_rounded),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 12, left: 4),
            child: Pressable(
              onTap: () => context.push('/profile/edit'),
              child: Hero(
                tag: 'me-avatar',
                child: HimeAvatar(name: me?.name ?? 'Me', path: me?.avatarPath, version: me?.avatarVersion ?? 0, size: 34),
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        tooltip: 'New chat',
        onPressed: () => context.push('/new-chat'),
        child: const Icon(Icons.add_comment_rounded),
      ),
      body: Column(children: [
        ValueListenableBuilder<bool>(
          valueListenable: core.online,
          builder: (_, online, __) => ConnectionBanner(online: online),
        ),
        Expanded(
          child: ListenableBuilder(
            listenable: Listenable.merge([core.chatList, core.profiles]),
            builder: (context, _) {
              final list = core.chatList;
              if (list.loading && list.chats.isEmpty) return const ListSkeleton();
              if (list.error != null && list.chats.isEmpty) {
                return ErrorState(error: list.error!, onRetry: list.refresh);
              }
              var chats = list.active;
              if (_filter == 1) chats = chats.where((c) => c.unread > 0).toList();
              if (_filter == 2) chats = chats.where((c) => c.isGroup).toList();
              final archivedCount = list.archived.length;
              return RefreshIndicator(
                color: HimeColors.ink,
                backgroundColor: HimeColors.yellow,
                onRefresh: () async {
                  await list.refresh();
                  await _loadPresence();
                },
                child: CustomScrollView(slivers: [
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(12, 4, 12, 6),
                      child: Wrap(spacing: 8, children: [
                        for (final (i, label) in [(0, 'All'), (1, 'Unread'), (2, 'Groups')])
                          ChoiceChip(
                            label: Text(label),
                            selected: _filter == i,
                            showCheckmark: false,
                            onSelected: (_) => setState(() => _filter = i),
                          ),
                      ]),
                    ),
                  ),
                  if (archivedCount > 0 && _filter == 0)
                    SliverToBoxAdapter(
                      child: ListTile(
                        leading: const SizedBox(width: 52, child: Icon(Icons.archive_outlined)),
                        title: const Text('Archived'),
                        trailing: Text('$archivedCount', style: context.text.labelMedium),
                        onTap: () => context.push('/archived'),
                      ),
                    ),
                  if (chats.isEmpty)
                    SliverFillRemaining(
                      hasScrollBody: false,
                      child: EmptyState(
                        icon: Icons.forum_rounded,
                        title: _filter == 0 ? 'Start a conversation' : 'Nothing here',
                        message: _filter == 0
                            ? 'Find friends by username or from your contacts. Your messages are end-to-end encrypted.'
                            : null,
                        action: _filter == 0
                            ? FilledButton.icon(
                                style: FilledButton.styleFrom(minimumSize: const Size(180, 46)),
                                onPressed: () => context.push('/new-chat'),
                                icon: const Icon(Icons.add_rounded),
                                label: const Text('New chat'),
                              )
                            : null,
                      ),
                    )
                  else
                    SliverList.builder(
                      itemCount: chats.length,
                      itemBuilder: (context, i) => ChatTile(
                        chat: chats[i],
                        core: core,
                        online: _presence[chats[i].otherUserId]?.online ?? false,
                      ),
                    ),
                  const SliverToBoxAdapter(child: SizedBox(height: 90)),
                ]),
              );
            },
          ),
        ),
      ]),
    );
  }
}

class ChatTile extends StatelessWidget {
  const ChatTile({super.key, required this.chat, required this.core, this.online = false});
  final ChatSummary chat;
  final HimeCore core;
  final bool online;

  void _actions(BuildContext context) {
    final list = core.chatList;
    showActionSheet(context, title: chat.title, actions: [
      SheetAction(chat.pinnedAt != null ? Icons.push_pin_outlined : Icons.push_pin_rounded,
          chat.pinnedAt != null ? 'Unpin chat' : 'Pin chat', () => guard(context, () => list.setPinned(chat.id, chat.pinnedAt == null))),
      SheetAction(chat.isMuted ? Icons.notifications_active_outlined : Icons.notifications_off_outlined,
          chat.isMuted ? 'Unmute' : 'Mute notifications', () async {
        if (chat.isMuted) {
          await guard(context, () => list.setMuted(chat.id, null));
        } else {
          final d = await pickMuteDuration(context);
          if (d != null && context.mounted) await guard(context, () => list.setMuted(chat.id, d));
        }
      }),
      SheetAction(chat.archived ? Icons.unarchive_outlined : Icons.archive_outlined, chat.archived ? 'Unarchive' : 'Archive',
          () => guard(context, () => list.setArchived(chat.id, !chat.archived))),
      SheetAction(Icons.cleaning_services_outlined, chat.isGroup ? 'Clear chat' : 'Delete chat', () async {
        final ok = await confirm(context,
            title: chat.isGroup ? 'Clear this chat?' : 'Delete this chat?',
            message: 'Messages will be removed from this phone. Others keep their copy.',
            confirmLabel: chat.isGroup ? 'Clear' : 'Delete',
            danger: true);
        if (ok && context.mounted) await guard(context, () => core.chats.clearChat(chat.id));
      }, danger: true),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final mine = chat.lastSenderId == core.userId;
    final sender = chat.isGroup && !mine && chat.lastSenderId != null && chat.lastKind != 'system' && chat.lastKind != 'call'
        ? '${core.profiles.nameOf(chat.lastSenderId)}: '
        : '';
    final preview = chat.lastPreview ?? '';
    final unread = chat.unread > 0;
    return InkWell(
      onTap: () => context.push('/chat/${chat.id}'),
      onLongPress: () => _actions(context),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        child: Row(children: [
          Hero(
            tag: 'avatar-${chat.id}',
            child: HimeAvatar(
              name: chat.title,
              path: chat.avatarPath,
              version: chat.avatarVersion,
              size: 52,
              online: online,
              icon: chat.isGroup ? (chat.isAnnouncement ? Icons.campaign_rounded : Icons.groups_rounded) : null,
            ),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(
                  child: Text(chat.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.text.titleMedium?.copyWith(fontWeight: unread ? FontWeight.w700 : FontWeight.w600)),
                ),
                const SizedBox(width: 8),
                Text(Fmt.chatTime(chat.lastAt),
                    style: context.text.labelSmall?.copyWith(
                      color: unread ? HimeColors.yellowDeep : context.palette.muted,
                      fontWeight: unread ? FontWeight.w700 : FontWeight.w500,
                    )),
              ]),
              const SizedBox(height: 3),
              Row(children: [
                if (mine && chat.lastMessageId != null && chat.lastKind != 'system' && chat.lastKind != 'call') ...[
                  DeliveryTicks(
                    state: deliveryFor(chat.lastAt, chat.peerDeliveredUpTo, chat.peerReadUpTo, 0),
                    size: 16,
                  ),
                  const SizedBox(width: 3),
                ],
                Expanded(
                  child: Text(
                    '$sender$preview',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.text.bodyMedium?.copyWith(
                      color: unread ? context.colors.onSurface : context.palette.muted,
                      fontStyle: chat.lastDeleted ? FontStyle.italic : null,
                    ),
                  ),
                ),
                if (chat.isMuted) Padding(padding: const EdgeInsets.only(left: 4), child: Icon(Icons.volume_off_rounded, size: 16, color: context.palette.muted)),
                if (chat.pinnedAt != null) Padding(padding: const EdgeInsets.only(left: 4), child: Icon(Icons.push_pin_rounded, size: 15, color: context.palette.muted)),
                if (unread) Padding(padding: const EdgeInsets.only(left: 6), child: UnreadBadge(count: chat.unread, muted: chat.isMuted)),
              ]),
            ]),
          ),
        ]),
      ),
    );
  }
}

Delivery deliveryFor(DateTime createdAt, DateTime? delivered, DateTime? read, int localState) {
  if (localState == 1) return Delivery.pending;
  if (localState == 2) return Delivery.failed;
  if (read != null && !read.isBefore(createdAt)) return Delivery.read;
  if (delivered != null && !delivered.isBefore(createdAt)) return Delivery.delivered;
  return Delivery.sent;
}

class DeliveryTicks extends StatelessWidget {
  const DeliveryTicks({super.key, required this.state, this.size = 15, this.color});
  final Delivery state;
  final double size;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final muted = color ?? context.palette.muted;
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 200),
      child: switch (state) {
        Delivery.pending => Icon(Icons.schedule_rounded, key: const ValueKey('p'), size: size - 2, color: muted),
        Delivery.failed => Icon(Icons.error_outline_rounded, key: const ValueKey('f'), size: size, color: context.colors.error),
        Delivery.sent => Icon(Icons.done_rounded, key: const ValueKey('s'), size: size, color: muted),
        Delivery.delivered => Icon(Icons.done_all_rounded, key: const ValueKey('d'), size: size, color: muted),
        Delivery.read => Icon(Icons.done_all_rounded, key: const ValueKey('r'), size: size, color: HimeColors.read),
      },
    );
  }
}

Future<Duration?> pickMuteDuration(BuildContext context) {
  return showModalBottomSheet<Duration>(
    context: context,
    builder: (ctx) => SafeArea(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Padding(padding: const EdgeInsets.only(bottom: 8), child: Text('Mute notifications for…', style: ctx.text.titleMedium)),
        for (final (label, d) in [
          ('8 hours', const Duration(hours: 8)),
          ('1 week', const Duration(days: 7)),
          ('Always', const Duration(days: 365 * 50)),
        ])
          ListTile(title: Text(label), onTap: () => Navigator.pop(ctx, d)),
        const SizedBox(height: 8),
      ]),
    ),
  );
}
