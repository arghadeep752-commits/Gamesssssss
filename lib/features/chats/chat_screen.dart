import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_contacts/flutter_contacts.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:share_plus/share_plus.dart';

import '../../app.dart';
import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import '../../services/session.dart';
import 'chat_controller.dart';
import 'chat_list_screen.dart';
import 'extra_screens.dart';
import 'message_widgets.dart';
import 'models.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key, required this.conversationId});
  final String conversationId;

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> with WidgetsBindingObserver {
  late final HimeCore core = ref.read(coreProvider);
  late final ChatController c = ChatController(core, widget.conversationId);
  // Created once (not on every build) so listeners aren't re-attached each frame.
  late final Listenable _changes = Listenable.merge([c, core.profiles]);
  final _scroll = ScrollController();
  ValueNotifier<PresenceInfo>? _presence;
  String? _presenceUser;
  ChatMessage? _replyTo;
  ChatMessage? _editing;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    c.open();
    c.addListener(_watchPeer);
    _scroll.addListener(() {
      if (_scroll.position.pixels > _scroll.position.maxScrollExtent - 600) c.loadMore();
    });
  }

  void _watchPeer() {
    final peer = c.summary?.otherUserId;
    if (peer != null && peer != _presenceUser) {
      if (_presenceUser != null) core.presence.unwatch(_presenceUser!);
      _presenceUser = peer;
      setState(() => _presence = core.presence.watch(peer));
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    c.setVisible(state == AppLifecycleState.resumed);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    if (_presenceUser != null) core.presence.unwatch(_presenceUser!);
    c.removeListener(_watchPeer);
    c.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _call(bool video) async {
    final s = c.summary;
    if (s == null || s.otherUserId == null) return;
    try {
      await core.calls.startCall(conversationId: s.id, peerId: s.otherUserId!, peerName: s.title, video: video);
    } catch (e) {
      if (mounted) toast(context, e is StateError ? e.message : friendlyError(e));
    }
  }

  void _onMessageLongPress(ChatMessage m) {
    final mine = m.senderId == core.userId;
    final s = c.summary;
    final canEdit = mine && m.kind == 'text' && !m.isDeleted && m.localState == 0 &&
        DateTime.now().toUtc().difference(m.createdAt) < const Duration(minutes: 15);
    final canDeleteAll = !m.isDeleted && m.localState == 0 && !m.isCall &&
        ((mine && DateTime.now().toUtc().difference(m.createdAt) < const Duration(days: 2)) || (s?.isGroup == true && s!.isAdmin));
    final myReaction = c.reactions[m.id]?[core.userId];
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
          if (!m.isDeleted && !m.isCall && m.localState == 0)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
                for (final e in quickReactions)
                  _ReactionButton(
                    emoji: e,
                    selected: myReaction == e,
                    onTap: () {
                      Navigator.pop(ctx);
                      guard(context, () async {
                        await core.chats.react(m, myReaction == e ? null : e);
                        final map = c.reactions[m.id] ??= {};
                        if (myReaction == e) {
                          map.remove(core.userId);
                        } else {
                          map[core.userId] = e;
                        }
                        setState(() {});
                      });
                    },
                  ),
              ]),
            ),
          if (!m.isDeleted && !m.isCall)
            ListTile(leading: const Icon(Icons.reply_rounded), title: const Text('Reply'), onTap: () {
              Navigator.pop(ctx);
              setState(() => _replyTo = m);
            }),
          if (m.text.isNotEmpty && !m.isDeleted)
            ListTile(leading: const Icon(Icons.copy_rounded), title: const Text('Copy'), onTap: () {
              Navigator.pop(ctx);
              Clipboard.setData(ClipboardData(text: m.text));
              toast(context, 'Copied');
            }),
          if (!m.isDeleted && !m.isCall && m.payload != null)
            ListTile(leading: const Icon(Icons.shortcut_rounded), title: const Text('Forward'), onTap: () {
              Navigator.pop(ctx);
              context.push('/forward', extra: ForwardArgs([m]));
            }),
          if (!m.isDeleted && m.localState == 0)
            ListTile(
              leading: Icon(c.starred.contains(m.id) ? Icons.star_outline_rounded : Icons.star_rounded),
              title: Text(c.starred.contains(m.id) ? 'Unstar' : 'Star'),
              onTap: () {
                Navigator.pop(ctx);
                final star = !c.starred.contains(m.id);
                guard(context, () async {
                  await core.chats.setStarred(m, star);
                  setState(() => star ? c.starred.add(m.id) : c.starred.remove(m.id));
                });
              },
            ),
          if (!m.isDeleted && m.localState == 0 && !m.isCall)
            ListTile(
              leading: Icon(c.pinned.contains(m.id) ? Icons.push_pin_outlined : Icons.push_pin_rounded),
              title: Text(c.pinned.contains(m.id) ? 'Unpin' : 'Pin'),
              onTap: () {
                Navigator.pop(ctx);
                guard(context, () async {
                  await core.chats.setPinned(m, !c.pinned.contains(m.id));
                  await c.loadPins();
                });
              },
            ),
          if (canEdit)
            ListTile(leading: const Icon(Icons.edit_rounded), title: const Text('Edit'), onTap: () {
              Navigator.pop(ctx);
              setState(() {
                _editing = m;
                _replyTo = null;
              });
            }),
          if (mine && m.localState == 0 && !m.isDeleted)
            ListTile(leading: const Icon(Icons.info_outline_rounded), title: const Text('Info'), onTap: () {
              Navigator.pop(ctx);
              context.push('/message-info', extra: MessageInfoArgs(m, c.summary));
            }),
          ListTile(leading: const Icon(Icons.delete_outline_rounded), title: const Text('Delete for me'), onTap: () {
            Navigator.pop(ctx);
            guard(context, () => core.chats.deleteForMe(m));
          }),
          if (canDeleteAll)
            ListTile(
              leading: Icon(Icons.delete_forever_rounded, color: ctx.colors.error),
              title: Text('Delete for everyone', style: TextStyle(color: ctx.colors.error)),
              onTap: () async {
                Navigator.pop(ctx);
                final ok = await confirm(context, title: 'Delete for everyone?', confirmLabel: 'Delete', danger: true);
                if (ok && mounted) await guard(context, () => core.chats.deleteForEveryone(m));
              },
            ),
          const SizedBox(height: 8),
        ]),
        ),
      ),
    );
  }

  Future<void> _menu(String value) async {
    final s = c.summary;
    switch (value) {
      case 'info':
        context.push('/chat/${widget.conversationId}/info');
      case 'search':
        context.push('/chat/${widget.conversationId}/search');
      case 'media':
        context.push('/chat/${widget.conversationId}/media');
      case 'mute':
        if (s == null) return;
        if (s.isMuted) {
          await guard(context, () => core.chatList.setMuted(s.id, null));
        } else {
          final d = await pickMuteDuration(context);
          if (d != null && mounted) await guard(context, () => core.chatList.setMuted(s.id, d));
        }
        setState(() {});
      case 'clear':
        final ok = await confirm(context, title: 'Clear this chat?', message: 'Messages are removed from this phone.', confirmLabel: 'Clear', danger: true);
        if (ok && mounted) await guard(context, () => core.chats.clearChat(widget.conversationId));
      case 'export':
        await _export();
      case 'block':
        if (s?.otherUserId == null) return;
        await toggleBlock(context, core, s!.otherUserId!, s.blockedByMe);
        await core.chatList.refresh();
        if (mounted) setState(() {});
      case 'report':
        if (!mounted) return;
        await showReportSheet(context, core, userId: s?.otherUserId, conversationId: widget.conversationId, recent: c.messages.take(5).toList());
    }
  }

  Future<void> _export() async {
    final rows = await core.chats.localPage(widget.conversationId, limit: 5000);
    final buf = StringBuffer('Hime chat export — ${c.summary?.title ?? ''}\n\n');
    for (final m in rows.reversed) {
      final who = m.senderId == core.userId ? 'You' : core.profiles.nameOf(m.senderId);
      final text = m.isSystem ? ChatMessage.systemLabel(m.system, (id) => core.profiles.nameOf(id)) : m.preview();
      buf.writeln('[${m.createdAt.toLocal()}] $who: $text');
    }
    final dir = await getTemporaryDirectory();
    final safe = (c.summary?.title ?? 'export').replaceAll(RegExp(r'[^\w\s-]'), '').trim();
    final f = File(p.join(dir.path, 'Hime chat - ${safe.isEmpty ? 'export' : safe}.txt'));
    await f.writeAsString(buf.toString());
    await SharePlus.instance.share(ShareParams(files: [XFile(f.path)], subject: 'Hime chat export'));
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _changes,
      builder: (context, _) {
        final s = c.summary;
        final title = s?.title ?? '';
        return Scaffold(
          backgroundColor: context.palette.chatBackground,
          appBar: AppBar(
            titleSpacing: 0,
            backgroundColor: context.colors.surface,
            title: InkWell(
              onTap: () => context.push('/chat/${widget.conversationId}/info'),
              child: Row(children: [
                Hero(
                  tag: 'avatar-${widget.conversationId}',
                  child: HimeAvatar(
                    name: title,
                    path: s?.avatarPath,
                    version: s?.avatarVersion ?? 0,
                    size: 38,
                    icon: s?.isGroup == true ? Icons.groups_rounded : null,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: context.text.titleMedium),
                    _Subtitle(controller: c, presence: _presence),
                  ]),
                ),
              ]),
            ),
            actions: [
              if (s != null && !s.isGroup && !s.blockedByMe) ...[
                IconButton(tooltip: 'Video call', icon: const Icon(Icons.videocam_outlined), onPressed: () => _call(true)),
                IconButton(tooltip: 'Voice call', icon: const Icon(Icons.call_outlined), onPressed: () => _call(false)),
              ],
              PopupMenuButton<String>(
                onSelected: _menu,
                itemBuilder: (_) => [
                  PopupMenuItem(value: 'info', child: Text(s?.isGroup == true ? 'Group info' : 'View contact')),
                  const PopupMenuItem(value: 'search', child: Text('Search')),
                  const PopupMenuItem(value: 'media', child: Text('Media, links and docs')),
                  PopupMenuItem(value: 'mute', child: Text(s?.isMuted == true ? 'Unmute notifications' : 'Mute notifications')),
                  const PopupMenuItem(value: 'export', child: Text('Export chat')),
                  const PopupMenuItem(value: 'clear', child: Text('Clear chat')),
                  if (s != null && !s.isGroup) PopupMenuItem(value: 'block', child: Text(s.blockedByMe ? 'Unblock' : 'Block')),
                  const PopupMenuItem(value: 'report', child: Text('Report')),
                ],
              ),
            ],
          ),
          body: Column(children: [
            if (c.pinned.isNotEmpty) _PinnedBar(controller: c, core: core),
            Expanded(child: _messageList(context)),
            if (s != null && s.blockedByMe)
              _InfoBar(
                text: 'You blocked this contact. Tap to unblock.',
                onTap: () => _menu('block'),
              )
            else if (s != null && !s.canSend)
              const _InfoBar(text: 'Only admins can send messages')
            else
              Composer(
                core: core,
                controller: c,
                enterSends: ref.read(sharedPrefsProvider).getBool('enter_sends') ?? false,
                replyTo: _replyTo,
                editing: _editing,
                onCancelReply: () => setState(() => _replyTo = null),
                onCancelEdit: () => setState(() => _editing = null),
                onSent: () {
                  setState(() {
                    _replyTo = null;
                    _editing = null;
                  });
                  if (_scroll.hasClients) _scroll.animateTo(0, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
                },
              ),
          ]),
        );
      },
    );
  }

  Widget _messageList(BuildContext context) {
    if (c.loading && c.messages.isEmpty) return const CenteredLoader();
    if (c.error != null && c.messages.isEmpty) return ErrorState(error: c.error!, onRetry: c.refreshLatest);
    if (c.messages.isEmpty) {
      return EmptyState(
        icon: Icons.lock_rounded,
        title: 'Say hi 👋',
        message: 'Messages and calls are end-to-end encrypted. Only people in this chat can read them.',
      );
    }
    final msgs = c.messages;
    final group = c.isGroup;
    return ListView.builder(
      controller: _scroll,
      reverse: true,
      padding: const EdgeInsets.only(top: 8, bottom: 8),
      itemCount: msgs.length + (c.loadingMore ? 1 : 0),
      itemBuilder: (context, i) {
        if (i == msgs.length) {
          return const Padding(padding: EdgeInsets.all(12), child: Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))));
        }
        final m = msgs[i];
        final older = i + 1 < msgs.length ? msgs[i + 1] : null;
        final newer = i > 0 ? msgs[i - 1] : null;
        final mine = m.senderId == core.userId;
        final newDay = older == null || !_sameDay(older.createdAt, m.createdAt);
        final groupedWithNext = newer != null &&
            newer.senderId == m.senderId &&
            !newer.isSystem &&
            _sameDay(newer.createdAt, m.createdAt) &&
            newer.createdAt.difference(m.createdAt) < const Duration(minutes: 3);
        final showSender = group && !mine && (older == null || older.senderId != m.senderId || older.isSystem || newDay);
        final fresh = DateTime.now().toUtc().difference(m.createdAt) < const Duration(seconds: 3);
        Widget bubble = MessageBubble(
          key: ValueKey(m.id),
          message: m,
          core: core,
          isMine: mine,
          delivery: c.deliveryOf(m),
          showSender: showSender,
          groupedWithNext: groupedWithNext,
          reactions: c.reactions[m.id],
          starred: c.starred.contains(m.id),
          onLongPress: () => _onMessageLongPress(m),
          onReply: m.isSystem || m.isCall ? null : () => setState(() => _replyTo = m),
          onRetry: () => core.chats.retry(m.id),
        );
        if (fresh) {
          bubble = TweenAnimationBuilder<double>(
            key: ValueKey('anim-${m.id}'),
            tween: Tween(begin: 0, end: 1),
            duration: const Duration(milliseconds: 260),
            curve: Curves.easeOutCubic,
            builder: (_, v, child) => Opacity(
              opacity: v,
              child: Transform.translate(offset: Offset(0, 14 * (1 - v)), child: child),
            ),
            child: bubble,
          );
        }
        return Column(children: [if (newDay) DateChip(date: m.createdAt), bubble]);
      },
    );
  }

  static bool _sameDay(DateTime a, DateTime b) {
    final x = a.toLocal(), y = b.toLocal();
    return x.year == y.year && x.month == y.month && x.day == y.day;
  }
}

class _ReactionButton extends StatelessWidget {
  const _ReactionButton({required this.emoji, required this.selected, required this.onTap});
  final String emoji;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Pressable(
        onTap: onTap,
        scale: 0.85,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: selected ? HimeColors.yellow : Colors.transparent, shape: BoxShape.circle),
          child: Text(emoji, style: const TextStyle(fontSize: 28)),
        ),
      );
}

class _Subtitle extends StatelessWidget {
  const _Subtitle({required this.controller, this.presence});
  final ChatController controller;
  final ValueNotifier<PresenceInfo>? presence;

  @override
  Widget build(BuildContext context) {
    final typing = controller.typingLabel();
    final style = context.text.labelMedium;
    if (typing != null) {
      return Row(children: [
        Text(typing, style: style?.copyWith(color: HimeColors.yellowDeep, fontWeight: FontWeight.w600)),
      ]);
    }
    final s = controller.summary;
    if (s == null) return const SizedBox.shrink();
    if (s.isGroup) {
      return Text('${s.memberCount} members', style: style, maxLines: 1, overflow: TextOverflow.ellipsis);
    }
    final p = presence;
    if (p == null) return const SizedBox.shrink();
    return ValueListenableBuilder<PresenceInfo>(
      valueListenable: p,
      builder: (_, info, __) {
        final text = info.online ? 'online' : Fmt.lastSeen(info.lastSeen);
        return AnimatedSwitcher(
          duration: const Duration(milliseconds: 200),
          child: Text(text, key: ValueKey(text), style: style?.copyWith(color: info.online ? HimeColors.online : null)),
        );
      },
    );
  }
}

class _PinnedBar extends StatelessWidget {
  const _PinnedBar({required this.controller, required this.core});
  final ChatController controller;
  final HimeCore core;

  @override
  Widget build(BuildContext context) {
    final byId = {for (final m in controller.messages) m.id: m};
    final first = controller.pinned.map((id) => byId[id]).whereType<ChatMessage>().firstOrNull;
    return Material(
      color: context.colors.surface,
      child: InkWell(
        onTap: () => showModalBottomSheet<void>(
          context: context,
          builder: (ctx) => SafeArea(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text('Pinned messages', style: ctx.text.titleMedium),
              for (final id in controller.pinned)
                ListTile(
                  leading: const Icon(Icons.push_pin_rounded),
                  title: Text(byId[id]?.preview() ?? 'Message not loaded', maxLines: 2, overflow: TextOverflow.ellipsis),
                  subtitle: byId[id] == null ? null : Text(core.profiles.nameOf(byId[id]!.senderId)),
                ),
              const SizedBox(height: 8),
            ]),
          ),
        ),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
          decoration: BoxDecoration(border: Border(bottom: BorderSide(color: context.palette.border))),
          child: Row(children: [
            const Icon(Icons.push_pin_rounded, size: 18, color: HimeColors.yellowDeep),
            const SizedBox(width: 10),
            Expanded(
              child: Text(first?.preview() ?? '${controller.pinned.length} pinned message(s)',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: context.text.bodyMedium),
            ),
            if (controller.pinned.length > 1) Text('${controller.pinned.length}', style: context.text.labelMedium),
          ]),
        ),
      ),
    );
  }
}

class _InfoBar extends StatelessWidget {
  const _InfoBar({required this.text, this.onTap});
  final String text;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: context.colors.surface,
        child: InkWell(
          onTap: onTap,
          child: SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Center(child: Text(text, style: context.text.bodyMedium?.copyWith(color: context.palette.muted))),
            ),
          ),
        ),
      );
}

/// Message input: text, emoji, attachments, voice notes, reply and edit.
class Composer extends StatefulWidget {
  const Composer({
    super.key,
    required this.core,
    required this.controller,
    this.replyTo,
    this.editing,
    required this.onCancelReply,
    required this.onCancelEdit,
    required this.onSent,
    this.enterSends = false,
  });

  final HimeCore core;
  final ChatController controller;
  final bool enterSends;
  final ChatMessage? replyTo;
  final ChatMessage? editing;
  final VoidCallback onCancelReply;
  final VoidCallback onCancelEdit;
  final VoidCallback onSent;

  @override
  State<Composer> createState() => _ComposerState();
}

class _ComposerState extends State<Composer> {
  final _text = TextEditingController();
  final _focus = FocusNode();
  bool _emoji = false;
  bool _hasText = false;
  Map<String, dynamic>? _link;
  String? _linkUrl;
  final _linkDebounce = Debouncer(const Duration(milliseconds: 700));

  // voice recording
  final _recorder = AudioRecorder();
  bool _recording = false;
  DateTime? _recStart;
  Timer? _recTimer;
  final _levels = <double>[];
  StreamSubscription<Amplitude>? _ampSub;

  HimeCore get core => widget.core;
  String get conv => widget.controller.conversationId;

  @override
  void initState() {
    super.initState();
    _text.addListener(_onText);
  }

  @override
  void didUpdateWidget(covariant Composer old) {
    super.didUpdateWidget(old);
    if (widget.editing != null && widget.editing != old.editing) {
      _text.text = widget.editing!.text;
      _focus.requestFocus();
    }
    if (widget.replyTo != null && widget.replyTo != old.replyTo) _focus.requestFocus();
  }

  void _onText() {
    final has = _text.text.trim().isNotEmpty;
    if (has != _hasText) setState(() => _hasText = has);
    if (has) widget.controller.sendTyping();
    final urls = findUrls(_text.text);
    if (urls.isEmpty) {
      if (_link != null || _linkUrl != null) {
        setState(() {
          _link = null;
          _linkUrl = null;
        });
      }
      return;
    }
    if (urls.first == _linkUrl) return;
    _linkUrl = urls.first;
    _linkDebounce(() async {
      final data = await LinkPreviewFetcher.fetch(urls.first);
      if (mounted && _linkUrl == urls.first) setState(() => _link = data);
    });
  }

  @override
  void dispose() {
    _text.dispose();
    _focus.dispose();
    _linkDebounce.dispose();
    _recTimer?.cancel();
    _ampSub?.cancel();
    _recorder.dispose();
    super.dispose();
  }

  Map<String, dynamic>? _replyPayload() {
    final r = widget.replyTo;
    if (r == null) return null;
    return {'id': r.id, 'sender': r.senderId, 'preview': r.preview()};
  }

  Future<void> _send() async {
    final text = _text.text.trim();
    if (text.isEmpty) return;
    final editing = widget.editing;
    _text.clear();
    widget.controller.sendTyping(stop: true);
    if (editing != null) {
      await guard(context, () => core.chats.editText(editing, text));
    } else {
      final mentions = <String>[];
      await core.chats.sendText(conv, text, reply: _replyPayload(), link: _link, mentions: mentions);
    }
    setState(() {
      _link = null;
      _linkUrl = null;
    });
    widget.onSent();
  }

  Future<void> _attach() async {
    _focus.unfocus();
    await showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: GridView.count(
            shrinkWrap: true,
            crossAxisCount: 3,
            mainAxisSpacing: 12,
            children: [
              _AttachOption(icon: Icons.photo_library_rounded, label: 'Gallery', color: const Color(0xFF8E5BD8), onTap: () {
                Navigator.pop(ctx);
                _pickGallery();
              }),
              _AttachOption(icon: Icons.camera_alt_rounded, label: 'Camera', color: const Color(0xFFE5486A), onTap: () {
                Navigator.pop(ctx);
                _pickCamera();
              }),
              _AttachOption(icon: Icons.videocam_rounded, label: 'Video', color: const Color(0xFF2F80ED), onTap: () {
                Navigator.pop(ctx);
                _pickVideo();
              }),
              _AttachOption(icon: Icons.insert_drive_file_rounded, label: 'Document', color: const Color(0xFF5B6CF0), onTap: () {
                Navigator.pop(ctx);
                _pickDocument();
              }),
              _AttachOption(icon: Icons.person_rounded, label: 'Contact', color: const Color(0xFF16A6B6), onTap: () {
                Navigator.pop(ctx);
                _pickContact();
              }),
              _AttachOption(icon: Icons.location_on_rounded, label: 'Location', color: const Color(0xFF2EB872), onTap: () {
                Navigator.pop(ctx);
                _shareLocation();
              }),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _sendImage(XFile x) async {
    try {
      final bytes = await x.readAsBytes();
      final codec = await ui.instantiateImageCodec(bytes, targetWidth: 24);
      final frame = await codec.getNextFrame();
      final png = await frame.image.toByteData(format: ui.ImageByteFormat.png);
      final full = await ui.instantiateImageCodec(bytes);
      final fullFrame = await full.getNextFrame();
      final extra = <String, dynamic>{
        'w': fullFrame.image.width,
        'h': fullFrame.image.height,
        if (png != null) 'thumb': base64Encode(png.buffer.asUint8List()),
      };
      frame.image.dispose();
      fullFrame.image.dispose();
      await core.chats.sendMedia(conv, 'image', File(x.path), extra: extra, name: p.basename(x.path), reply: _replyPayload());
      widget.onSent();
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
  }

  Future<void> _pickGallery() async {
    final picks = await ImagePicker().pickMultiImage(maxWidth: 1600, maxHeight: 1600, imageQuality: 80, limit: 10);
    for (final x in picks) {
      await _sendImage(x);
    }
  }

  Future<void> _pickCamera() async {
    final x = await ImagePicker().pickImage(source: ImageSource.camera, maxWidth: 1600, maxHeight: 1600, imageQuality: 80);
    if (x != null) await _sendImage(x);
  }

  Future<void> _pickVideo() async {
    final x = await ImagePicker().pickVideo(source: ImageSource.gallery, maxDuration: const Duration(minutes: 5));
    if (x == null || !mounted) return;
    await guard(context, () async {
      await core.chats.sendMedia(conv, 'video', File(x.path), name: p.basename(x.path), reply: _replyPayload());
      widget.onSent();
    });
  }

  Future<void> _pickDocument() async {
    final x = await openFile();
    if (x == null || !mounted) return;
    await guard(context, () async {
      await core.chats.sendMedia(conv, 'document', File(x.path), name: x.name, reply: _replyPayload());
      widget.onSent();
    });
  }

  Future<void> _pickContact() async {
    if (!await FlutterContacts.requestPermission(readonly: true)) {
      if (mounted) toast(context, 'Allow contacts access to share a contact');
      return;
    }
    final picked = await FlutterContacts.openExternalPick();
    if (picked == null) return;
    final full = await FlutterContacts.getContact(picked.id, withProperties: true) ?? picked;
    await core.chats.sendPayload(conv, 'contact', {
      'contact': {'name': full.displayName, 'phones': full.phones.map((ph) => ph.number).toList()},
      'reply': ?_replyPayload(),
    });
    widget.onSent();
  }

  Future<void> _shareLocation() async {
    final ok = await confirm(context, title: 'Share your current location?', message: 'Your location is sent end-to-end encrypted to this chat.', confirmLabel: 'Share');
    if (!ok || !mounted) return;
    await guard(context, () async {
      if (!await Geolocator.isLocationServiceEnabled()) throw StateError('Turn on location services first.');
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
      if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
        throw StateError('Location permission is needed.');
      }
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 20)),
      );
      await core.chats.sendPayload(conv, 'location', {
        'location': {'lat': pos.latitude, 'lng': pos.longitude, 'acc': pos.accuracy},
      });
      widget.onSent();
    });
  }

  // ---------------- voice notes
  Future<void> _startRecording() async {
    if (!await Permission.microphone.request().isGranted) {
      if (mounted) toast(context, 'Allow microphone access to record voice messages');
      return;
    }
    final dir = await getTemporaryDirectory();
    final path = p.join(dir.path, 'voice_${DateTime.now().millisecondsSinceEpoch}.m4a');
    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.aacLc, bitRate: 48000, sampleRate: 22050, numChannels: 1),
      path: path,
    );
    HapticFeedback.mediumImpact();
    _levels.clear();
    _ampSub = _recorder.onAmplitudeChanged(const Duration(milliseconds: 120)).listen((a) {
      final v = ((a.current + 50) / 50).clamp(0.05, 1.0);
      _levels.add(v);
    });
    setState(() {
      _recording = true;
      _recStart = DateTime.now();
    });
    _recTimer = Timer.periodic(const Duration(milliseconds: 250), (_) => setState(() {}));
  }

  Future<void> _stopRecording({required bool send}) async {
    _recTimer?.cancel();
    await _ampSub?.cancel();
    final started = _recStart;
    final path = await _recorder.stop();
    setState(() => _recording = false);
    if (!send || path == null || started == null) return;
    final ms = DateTime.now().difference(started).inMilliseconds;
    if (ms < 800) {
      if (mounted) toast(context, 'Hold on a little longer to record');
      return;
    }
    final wave = _downsample(_levels, 40);
    if (!mounted) return;
    await guard(context, () async {
      await core.chats.sendMedia(conv, 'voice', File(path),
          name: 'voice.m4a', mime: 'audio/mp4', extra: {'dur': ms, 'wave': wave}, reply: _replyPayload());
      widget.onSent();
    });
  }

  static List<double> _downsample(List<double> v, int n) {
    if (v.isEmpty) return [];
    if (v.length <= n) return v.map((e) => double.parse(e.toStringAsFixed(2))).toList();
    final out = <double>[];
    final step = v.length / n;
    for (var i = 0; i < n; i++) {
      final slice = v.sublist((i * step).floor(), ((i + 1) * step).floor().clamp(0, v.length));
      final m = slice.isEmpty ? 0.0 : slice.reduce((a, b) => a > b ? a : b);
      out.add(double.parse(m.toStringAsFixed(2)));
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final reply = widget.replyTo;
    final editing = widget.editing;
    return Container(
      color: context.colors.surface,
      child: SafeArea(
        top: false,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          if (reply != null || editing != null)
            Container(
              margin: const EdgeInsets.fromLTRB(10, 8, 10, 0),
              padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
              decoration: BoxDecoration(
                color: context.colors.surfaceContainer,
                borderRadius: BorderRadius.circular(12),
                border: const Border(left: BorderSide(color: HimeColors.yellowDeep, width: 3)),
              ),
              child: Row(children: [
                Icon(editing != null ? Icons.edit_rounded : Icons.reply_rounded, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(editing != null ? 'Edit message' : 'Replying to ${reply!.senderId == core.userId ? 'yourself' : core.profiles.nameOf(reply.senderId)}',
                        style: context.text.labelMedium?.copyWith(fontWeight: FontWeight.w700, color: HimeColors.yellowDeep)),
                    Text((editing ?? reply)!.preview(), maxLines: 1, overflow: TextOverflow.ellipsis, style: context.text.bodySmall),
                  ]),
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 20),
                  onPressed: () {
                    if (editing != null) {
                      _text.clear();
                      widget.onCancelEdit();
                    } else {
                      widget.onCancelReply();
                    }
                  },
                ),
              ]),
            ),
          if (_link != null && editing == null)
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 8, 10, 0),
              child: Row(children: [
                Expanded(child: LinkPreviewCard(data: _link!)),
                IconButton(icon: const Icon(Icons.close_rounded, size: 18), onPressed: () => setState(() => _link = null)),
              ]),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(6, 6, 6, 6),
            child: _recording ? _recordingBar(context) : _inputRow(context),
          ),
          if (_emoji)
            EmojiPanel(onPick: (e) {
              final sel = _text.selection;
              final t = _text.text;
              final start = sel.start < 0 ? t.length : sel.start;
              final end = sel.end < 0 ? t.length : sel.end;
              _text.value = TextEditingValue(
                text: t.replaceRange(start, end, e),
                selection: TextSelection.collapsed(offset: start + e.length),
              );
            }),
        ]),
      ),
    );
  }

  Widget _inputRow(BuildContext context) {
    final editing = widget.editing != null;
    return Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
      Expanded(
        child: Container(
          decoration: BoxDecoration(
            color: context.colors.surfaceContainer,
            borderRadius: BorderRadius.circular(24),
          ),
          child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            IconButton(
              tooltip: 'Emoji',
              icon: Icon(_emoji ? Icons.keyboard_rounded : Icons.emoji_emotions_outlined),
              onPressed: () {
                setState(() => _emoji = !_emoji);
                if (_emoji) {
                  _focus.unfocus();
                } else {
                  _focus.requestFocus();
                }
              },
            ),
            Expanded(
              child: TextField(
                controller: _text,
                focusNode: _focus,
                minLines: 1,
                maxLines: 6,
                textCapitalization: TextCapitalization.sentences,
                keyboardType: widget.enterSends ? TextInputType.text : TextInputType.multiline,
                textInputAction: widget.enterSends ? TextInputAction.send : TextInputAction.newline,
                onSubmitted: widget.enterSends ? (_) => _send() : null,
                onTap: () => setState(() => _emoji = false),
                decoration: const InputDecoration(
                  hintText: 'Message',
                  filled: false,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
            if (!editing) IconButton(tooltip: 'Attach', icon: const Icon(Icons.attach_file_rounded), onPressed: _attach),
          ]),
        ),
      ),
      const SizedBox(width: 6),
      Pressable(
        onTap: _hasText || editing ? _send : _startRecording,
        scale: 0.9,
        child: Container(
          width: 48,
          height: 48,
          decoration: const BoxDecoration(color: HimeColors.yellow, shape: BoxShape.circle),
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 160),
            transitionBuilder: (child, a) => ScaleTransition(scale: a, child: child),
            child: Icon(
              _hasText || editing ? (editing ? Icons.check_rounded : Icons.send_rounded) : Icons.mic_rounded,
              key: ValueKey(_hasText || editing),
              color: HimeColors.ink,
            ),
          ),
        ),
      ),
    ]);
  }

  Widget _recordingBar(BuildContext context) {
    final elapsed = _recStart == null ? Duration.zero : DateTime.now().difference(_recStart!);
    return Row(children: [
      IconButton(
        tooltip: 'Cancel',
        icon: Icon(Icons.delete_outline_rounded, color: context.colors.error),
        onPressed: () => _stopRecording(send: false),
      ),
      const _RecDot(),
      const SizedBox(width: 8),
      Text(Fmt.duration(elapsed), style: context.text.titleSmall),
      const SizedBox(width: 12),
      Expanded(child: Text('Recording…', style: context.text.bodyMedium?.copyWith(color: context.palette.muted))),
      Pressable(
        onTap: () => _stopRecording(send: true),
        child: Container(
          width: 48,
          height: 48,
          decoration: const BoxDecoration(color: HimeColors.yellow, shape: BoxShape.circle),
          child: const Icon(Icons.send_rounded, color: HimeColors.ink),
        ),
      ),
    ]);
  }
}

class _RecDot extends StatefulWidget {
  const _RecDot();
  @override
  State<_RecDot> createState() => _RecDotState();
}

class _RecDotState extends State<_RecDot> with SingleTickerProviderStateMixin {
  late final AnimationController _a = AnimationController(vsync: this, duration: const Duration(milliseconds: 800))..repeat(reverse: true);
  @override
  void dispose() {
    _a.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => FadeTransition(
        opacity: _a,
        child: Container(width: 10, height: 10, decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle)),
      );
}

class _AttachOption extends StatelessWidget {
  const _AttachOption({required this.icon, required this.label, required this.color, required this.onTap});
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Pressable(
        onTap: onTap,
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Container(
            width: 58,
            height: 58,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            child: Icon(icon, color: Colors.white, size: 26),
          ),
          const SizedBox(height: 8),
          Text(label, style: context.text.labelMedium?.copyWith(color: context.colors.onSurface)),
        ]),
      );
}
