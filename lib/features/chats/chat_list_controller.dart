import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../../services/core.dart';
import 'models.dart';

/// Chat list state: server snapshot + live realtime updates + offline cache.
class ChatListController extends ChangeNotifier {
  ChatListController(this.core) {
    _subs.add(core.realtime.receipts.listen(_onReceipt));
    _subs.add(core.realtime.conversations.listen((_) => refresh()));
  }

  final HimeCore core;
  final _subs = <StreamSubscription<dynamic>>[];

  List<ChatSummary> chats = [];
  bool loading = true;
  Object? error;
  bool _refreshing = false;
  bool _again = false;
  final _previews = <String, String>{};

  List<ChatSummary> get active => chats.where((c) => !c.archived).toList();
  List<ChatSummary> get archived => chats.where((c) => c.archived).toList();
  int get unreadChats => chats.where((c) => c.unread > 0 && !c.archived).length;

  ChatSummary? byId(String id) {
    for (final c in chats) {
      if (c.id == id) return c;
    }
    return null;
  }

  Future<void> loadCached() async {
    final raw = await core.db.getKv('chat_list');
    if (raw == null) return;
    try {
      final list = (jsonDecode(raw) as List).cast<Map<String, dynamic>>();
      chats = list.map(ChatSummary.fromRpc).toList();
      for (final c in chats) {
        c.lastPreview = c.raw?['_preview'] as String?;
      }
      loading = false;
      notifyListeners();
    } catch (_) {}
  }

  Future<void> refresh() async {
    if (_refreshing) {
      _again = true;
      return;
    }
    _refreshing = true;
    try {
      do {
        _again = false;
        final rows = (await core.sb.rpc('get_chats', params: {'p_device_id': core.deviceId}) as List<dynamic>)
            .cast<Map<String, dynamic>>();
        final next = <ChatSummary>[];
        for (final r in rows) {
          final c = ChatSummary.fromRpc(r);
          c.lastPreview = await _preview(c, r);
          next.add(c);
        }
        chats = next;
        error = null;
        loading = false;
        _sort();
        notifyListeners();
        unawaited(core.profiles.ensure(chats.map((c) => c.lastSenderId)));
        unawaited(core.db.setKv(
            'chat_list',
            jsonEncode([
              for (final c in chats) {...?c.raw, '_preview': c.lastPreview},
            ])));
      } while (_again);
    } catch (e) {
      error = e;
      loading = false;
      notifyListeners();
    } finally {
      _refreshing = false;
    }
  }

  Future<String> _preview(ChatSummary c, Map<String, dynamic> r) async {
    final id = c.lastMessageId;
    if (id == null) return c.isGroup ? 'Group created' : '';
    if (c.lastDeleted) return 'This message was deleted';
    final cached = _previews[id];
    if (cached != null && !c.lastEdited) return cached;
    final local = await core.db.message(id);
    String text;
    if (local != null && local.payload != null && (local.editedAt != null) == c.lastEdited) {
      text = ChatMessage.previewFor(local.kind, local.payload);
    } else if (c.lastKind == 'system') {
      text = ChatMessage.systemLabel(
          r['last_system'] is Map ? Map<String, dynamic>.from(r['last_system'] as Map) : null, (id) => core.profiles.nameOf(id));
    } else if (c.lastKind == 'call') {
      text = ChatMessage.callLabel(r['last_system'] is Map ? Map<String, dynamic>.from(r['last_system'] as Map) : null);
    } else {
      try {
        final m = await core.chats.ingestRow({
          'id': id,
          'conversation_id': c.id,
          'sender_id': c.lastSenderId,
          'sender_device_id': r['last_sender_device_id'],
          'kind': c.lastKind,
          'ciphertext': r['last_ciphertext'],
          'nonce': r['last_nonce'],
          'eph_key': r['last_eph_key'],
          'wrapped_key': r['last_wrapped_key'],
          'system': r['last_system'],
          'created_at': r['last_message_at'],
          'updated_at': r['last_message_at'],
        });
        text = m.undecryptable ? 'Encrypted message' : m.preview();
      } catch (_) {
        text = 'Encrypted message';
      }
    }
    _previews[id] = text;
    return text;
  }

  void _sort() {
    chats.sort((a, b) {
      if ((a.pinnedAt != null) != (b.pinnedAt != null)) return a.pinnedAt != null ? -1 : 1;
      if (a.pinnedAt != null && b.pinnedAt != null) return b.pinnedAt!.compareTo(a.pinnedAt!);
      return b.lastAt.compareTo(a.lastAt);
    });
  }

  /// Live update from the chat engine.
  void onMessage(ChatMessage m, {required bool isNew}) {
    final c = byId(m.conversationId);
    if (c == null) {
      unawaited(refresh());
      return;
    }
    if (c.lastMessageId == m.id || isNew || m.createdAt.isAfter(c.lastAt) || c.lastMessageId == null) {
      c.lastMessageId = m.id;
      c.lastAt = m.createdAt;
      c.lastKind = m.kind;
      c.lastSenderId = m.senderId;
      c.lastDeleted = m.isDeleted;
      c.lastPreview = m.isSystem ? ChatMessage.systemLabel(m.system, (id) => core.profiles.nameOf(id)) : m.preview();
      _previews[m.id] = c.lastPreview!;
      if (isNew && m.senderId != core.userId && core.openConversationId != m.conversationId && !m.isSystem) {
        c.unread += 1;
      }
      if (isNew && c.archived && m.senderId != core.userId && !c.isMuted) {
        c.archived = false;
      }
      _sort();
      notifyListeners();
    }
  }

  void _onReceipt(Map<String, dynamic> e) {
    final c = byId(e['conversation_id'] as String? ?? '');
    if (c == null) return;
    if (c.isGroup) {
      unawaited(refresh());
      return;
    }
    c.peerDeliveredUpTo = DateTime.tryParse('${e['delivered_up_to']}') ?? c.peerDeliveredUpTo;
    c.peerReadUpTo = DateTime.tryParse('${e['read_up_to']}') ?? c.peerReadUpTo;
    notifyListeners();
  }

  void markOpened(String conversationId) {
    final c = byId(conversationId);
    if (c != null && c.unread != 0) {
      c.unread = 0;
      notifyListeners();
    }
  }

  Future<void> _state(String id, Map<String, dynamic> values) async {
    await core.sb.from('conversation_member_state').update(values).eq('conversation_id', id).eq('user_id', core.userId);
    await refresh();
  }

  Future<void> setArchived(String id, bool v) => _state(id, {'archived': v});
  Future<void> setPinned(String id, bool v) async {
    if (v && chats.where((c) => c.pinnedAt != null).length >= 3) {
      throw StateError('You can pin up to 3 chats');
    }
    await _state(id, {'pinned_at': v ? DateTime.now().toUtc().toIso8601String() : null});
  }

  Future<void> setMuted(String id, Duration? d) =>
      _state(id, {'muted_until': d == null ? null : DateTime.now().toUtc().add(d).toIso8601String()});

  @override
  void dispose() {
    for (final s in _subs) {
      s.cancel();
    }
    super.dispose();
  }
}
