import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/utils.dart';
import '../../services/core.dart';
import '../../services/notifications.dart';
import 'chat_repository.dart';
import 'models.dart';

/// State of one open conversation.
class ChatController extends ChangeNotifier {
  ChatController(this.core, this.conversationId) {
    _subs.add(core.chats.events.where((e) => e.conversationId == conversationId).listen(_onEvent));
    _subs.add(core.realtime.receipts.where((e) => e['conversation_id'] == conversationId).listen(_onReceipt));
    _subs.add(core.realtime.reactions.where((e) => e['conversation_id'] == conversationId).listen(_onReaction));
    _subs.add(core.realtime.pins.where((e) => e['conversation_id'] == conversationId).listen((_) => loadPins()));
    _subs.add(core.realtime.conversations.where((e) => e['conversation_id'] == conversationId).listen((_) => _refreshSummary()));
  }

  final HimeCore core;
  final String conversationId;
  final _subs = <StreamSubscription<dynamic>>[];

  final List<ChatMessage> messages = [];
  Map<String, Map<String, String>> reactions = {};
  Set<String> starred = {};
  List<String> pinned = [];
  bool loading = true;
  bool loadingMore = false;
  bool hasMore = true;
  Object? error;

  ChatSummary? summary;
  DateTime? peerDelivered;
  DateTime? peerRead;
  final typing = <String, DateTime>{};
  Timer? _typingSweep;
  RealtimeChannel? _convChannel;
  DateTime _lastTypingSent = DateTime.fromMillisecondsSinceEpoch(0);
  Timer? _readDebounce;
  bool visible = true;

  bool get isGroup => summary?.isGroup ?? false;

  Future<void> open() async {
    core.openConversationId = conversationId;
    core.chatList.markOpened(conversationId);
    unawaited(NotificationService.instance.clearChat(conversationId));
    _refreshSummary();
    final local = await core.chats.localPage(conversationId);
    _merge(local);
    loading = local.isEmpty;
    notifyListeners();
    _joinTyping();
    unawaited(loadPins());
    unawaited(_loadExtras());
    await refreshLatest();
  }

  void _refreshSummary() {
    summary = core.chatList.byId(conversationId);
    peerDelivered = summary?.peerDeliveredUpTo;
    peerRead = summary?.peerReadUpTo;
    if (summary == null) {
      unawaited(core.chatList.refresh().then((_) {
        summary = core.chatList.byId(conversationId);
        peerDelivered = summary?.peerDeliveredUpTo;
        peerRead = summary?.peerReadUpTo;
        notifyListeners();
      }));
    }
    notifyListeners();
  }

  Future<void> refreshLatest() async {
    try {
      final fresh = await core.chats.fetchPage(conversationId, limit: 40);
      _merge(fresh, authoritativeWindow: true);
      hasMore = fresh.length >= 40;
      error = null;
    } catch (e) {
      error = messages.isEmpty ? e : null;
    }
    loading = false;
    notifyListeners();
    _markRead();
    unawaited(core.profiles.ensure(messages.map((m) => m.senderId)));
  }

  Future<void> _loadExtras() async {
    reactions = await core.chats.loadReactions(conversationId);
    try {
      starred = await core.chats.starredIds(conversationId);
    } catch (_) {}
    notifyListeners();
  }

  Future<void> loadPins() async {
    try {
      pinned = await core.chats.pinnedIds(conversationId);
      notifyListeners();
    } catch (_) {}
  }

  Future<void> loadMore() async {
    if (loadingMore || !hasMore || messages.isEmpty) return;
    loadingMore = true;
    notifyListeners();
    final before = messages.last.createdAt;
    try {
      var page = await core.chats.localPage(conversationId, before: before, limit: 40);
      if (page.length < 40) {
        page = await core.chats.fetchPage(conversationId, before: before, limit: 40);
        hasMore = page.length >= 40;
      }
      _merge(page);
    } catch (_) {}
    loadingMore = false;
    notifyListeners();
  }

  void _merge(List<ChatMessage> incoming, {bool authoritativeWindow = false}) {
    final byId = {for (final m in messages) m.id: m};
    for (final m in incoming) {
      byId[m.id] = m;
    }
    messages
      ..clear()
      ..addAll(byId.values)
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
  }

  void _onEvent(ChatEvent e) {
    if (e.reload) {
      messages.clear();
      notifyListeners();
      unawaited(refreshLatest());
      return;
    }
    if (e.removedId != null) {
      messages.removeWhere((m) => m.id == e.removedId);
      notifyListeners();
      return;
    }
    final m = e.message;
    if (m == null) return;
    final i = messages.indexWhere((x) => x.id == m.id);
    if (i >= 0) {
      messages[i] = m;
      messages.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    } else {
      messages.insert(0, m);
      messages.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      if (m.senderId != null) typing.remove(m.senderId);
    }
    if (m.isDeleted) {
      reactions.remove(m.id);
      pinned.remove(m.id);
    }
    notifyListeners();
    if (m.senderId != core.userId) _markRead();
  }

  void _onReceipt(Map<String, dynamic> e) {
    if (e['user_id'] == core.userId) return;
    if (isGroup) {
      unawaited(core.chatList.refresh().then((_) => _refreshSummary()));
      return;
    }
    peerDelivered = parseTime(e['delivered_up_to']) ?? peerDelivered;
    peerRead = parseTime(e['read_up_to']) ?? peerRead;
    notifyListeners();
  }

  void _onReaction(Map<String, dynamic> e) {
    final mid = e['message_id'] as String;
    final uid = e['user_id'] as String;
    final emoji = e['emoji'] as String?;
    final map = reactions[mid] ??= {};
    if (emoji == null) {
      map.remove(uid);
    } else {
      map[uid] = emoji;
    }
    unawaited(core.db.setReaction(conversationId, mid, uid, emoji));
    notifyListeners();
  }

  void _markRead() {
    if (!visible) return;
    _readDebounce?.cancel();
    _readDebounce = Timer(const Duration(milliseconds: 600), () {
      final latest = messages.where((m) => m.senderId != core.userId && m.localState == 0).firstOrNull;
      if (latest != null) unawaited(core.chats.markRead(conversationId, latest.createdAt));
      core.chatList.markOpened(conversationId);
    });
  }

  void setVisible(bool v) {
    visible = v;
    if (v) {
      core.openConversationId = conversationId;
      _markRead();
    } else if (core.openConversationId == conversationId) {
      core.openConversationId = null;
    }
  }

  // ------------------------------------------------------------ typing
  void _joinTyping() {
    final ch = core.sb.channel('conv:$conversationId', opts: const RealtimeChannelConfig(private: true));
    ch.onBroadcast(event: 'typing', callback: (p) {
      final data = p['payload'] is Map ? Map<String, dynamic>.from(p['payload'] as Map) : p;
      final uid = data['user_id'] as String?;
      if (uid == null || uid == core.userId) return;
      if (data['stop'] == true) {
        typing.remove(uid);
      } else {
        typing[uid] = DateTime.now();
      }
      notifyListeners();
    }).subscribe();
    _convChannel = ch;
    _typingSweep = Timer.periodic(const Duration(seconds: 2), (_) {
      final before = typing.length;
      typing.removeWhere((_, t) => DateTime.now().difference(t) > const Duration(seconds: 5));
      if (typing.length != before) notifyListeners();
    });
  }

  void sendTyping({bool stop = false}) {
    final ch = _convChannel;
    if (ch == null) return;
    final now = DateTime.now();
    if (!stop && now.difference(_lastTypingSent) < const Duration(seconds: 3)) return;
    _lastTypingSent = stop ? DateTime.fromMillisecondsSinceEpoch(0) : now;
    unawaited(ch.sendBroadcastMessage(event: 'typing', payload: {'user_id': core.userId, 'stop': stop}).then((_) {}, onError: (_) {}));
  }

  String? typingLabel() {
    if (typing.isEmpty) return null;
    if (!isGroup) return 'typing…';
    final names = typing.keys.map((id) => core.profiles.nameOf(id).split(' ').first).toList();
    return names.length == 1 ? '${names.first} is typing…' : '${names.length} people are typing…';
  }

  Delivery deliveryOf(ChatMessage m) {
    if (m.localState == 1) return Delivery.pending;
    if (m.localState == 2) return Delivery.failed;
    if (peerRead != null && !peerRead!.isBefore(m.createdAt)) return Delivery.read;
    if (peerDelivered != null && !peerDelivered!.isBefore(m.createdAt)) return Delivery.delivered;
    return Delivery.sent;
  }

  @override
  void dispose() {
    for (final s in _subs) {
      s.cancel();
    }
    _typingSweep?.cancel();
    _readDebounce?.cancel();
    sendTyping(stop: true);
    final ch = _convChannel;
    if (ch != null) unawaited(core.sb.removeChannel(ch));
    if (core.openConversationId == conversationId) core.openConversationId = null;
    super.dispose();
  }
}
