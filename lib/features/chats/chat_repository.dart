import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

import '../../core/utils.dart';
import '../../services/core.dart';
import '../../services/e2ee.dart';
import '../../services/local_db.dart';
import '../../services/notifications.dart';
import 'models.dart';

/// What changed in a conversation (drives chat screens and the chat list).
class ChatEvent {
  ChatEvent(this.conversationId, {this.message, this.removedId, this.reload = false});
  final String conversationId;
  final ChatMessage? message;
  final String? removedId;
  final bool reload;
}

/// Messaging engine: encryption, the offline outbox, sync and media.
class ChatRepository {
  ChatRepository(this.core);
  final HimeCore core;
  SupabaseClient get sb => core.sb;
  LocalDb get db => core.db;

  static const _uuid = Uuid();
  static const maxMediaBytes = 48 * 1024 * 1024;

  final _events = StreamController<ChatEvent>.broadcast();
  Stream<ChatEvent> get events => _events.stream;

  /// Upload / download progress per message id (0..1).
  final progress = <String, ValueNotifier<double>>{};

  final _devices = <String, (DateTime, Map<String, String>)>{};
  bool _syncing = false;
  bool _syncAgain = false;
  bool _flushing = false;

  // ---------------------------------------------------------------- devices
  Future<Map<String, String>> conversationDevices(String conversationId, {bool refresh = false}) async {
    final hit = _devices[conversationId];
    if (!refresh && hit != null && DateTime.now().difference(hit.$1) < const Duration(minutes: 5)) return hit.$2;
    final rows = (await sb.rpc('get_conversation_devices', params: {'p_conversation_id': conversationId}) as List<dynamic>)
        .cast<Map<String, dynamic>>();
    await db.rememberDevices(rows);
    final map = {for (final r in rows) r['device_id'] as String: r['identity_key'] as String};
    _devices[conversationId] = (DateTime.now(), map);
    return map;
  }

  Future<String?> _deviceKey(String deviceId, String conversationId) async {
    if (deviceId == core.deviceId) return core.e2ee.publicKeyB64;
    final local = await db.deviceKey(deviceId);
    if (local != null) return local;
    final fresh = await conversationDevices(conversationId, refresh: true);
    return fresh[deviceId];
  }

  // ------------------------------------------------------------- decryption
  static ChatMessage fromLocal(LocalMessageRow r) => ChatMessage(
        id: r.id,
        conversationId: r.conversationId,
        senderId: r.senderId,
        senderDeviceId: r.senderDeviceId,
        kind: r.kind,
        payload: r.payload,
        system: r.system,
        createdAt: r.createdAt,
        editedAt: r.editedAt,
        deletedAt: r.deletedAt,
        localState: r.localState,
        undecryptable: r.undecryptable,
      );

  /// Decrypts a server row (from RPC or realtime) and caches it locally.
  Future<ChatMessage> ingestRow(Map<String, dynamic> r) async {
    final id = r['id'] as String;
    final conv = r['conversation_id'] as String;
    final kind = r['kind'] as String;
    final updatedAt = parseTime(r['updated_at']) ?? DateTime.now().toUtc();
    final createdAt = parseTime(r['created_at']) ?? updatedAt;
    final deletedAt = parseTime(r['deleted_at']);
    final cached = await db.message(id);
    if (cached != null && !cached.updatedAt.isBefore(updatedAt) && !cached.undecryptable && cached.localState == 0) {
      return fromLocal(cached);
    }
    Map<String, dynamic>? payload;
    var undecryptable = false;
    final system = r['system'] is Map ? Map<String, dynamic>.from(r['system'] as Map) : null;
    final senderDevice = r['sender_device_id'] as String?;
    if (deletedAt == null && kind != 'system' && kind != 'call') {
      final keys = r['keys'];
      final wrapped = (r['wrapped_key'] as String?) ?? (keys is Map ? keys[core.deviceId] as String? : null);
      final ct = r['ciphertext'] as String?;
      if (wrapped == null || ct == null || senderDevice == null) {
        undecryptable = true;
      } else {
        try {
          final senderKey = await _deviceKey(senderDevice, conv);
          if (senderKey == null) throw StateError('unknown sender device');
          payload = await core.e2ee.open(
            ciphertext: ct,
            nonce: r['nonce'] as String,
            ephKey: r['eph_key'] as String,
            wrappedKey: wrapped,
            senderPublicKey: senderKey,
            messageId: id,
            conversationId: conv,
            senderId: r['sender_id'] as String,
            senderDeviceId: senderDevice,
          );
        } catch (e) {
          debugPrint('decrypt $id failed: $e');
          undecryptable = true;
          payload = cached?.payload;
          if (payload != null) undecryptable = false;
        }
      }
    }
    final row = LocalMessageRow(
      id: id,
      conversationId: conv,
      senderId: r['sender_id'] as String?,
      senderDeviceId: senderDevice,
      kind: kind,
      payload: deletedAt == null ? payload : null,
      system: system,
      createdAt: createdAt,
      updatedAt: updatedAt,
      editedAt: parseTime(r['edited_at']),
      deletedAt: deletedAt,
      undecryptable: undecryptable,
    );
    await db.upsertMessage(row);
    return fromLocal(row);
  }

  Future<void> ingestRealtime(Map<String, dynamic> data) async {
    try {
      final isNew = data['op'] == 'insert';
      final m = await ingestRow(data);
      _events.add(ChatEvent(m.conversationId, message: m));
      core.chatList.onMessage(m, isNew: isNew);
      if (isNew && m.senderId != core.userId) {
        if (core.openConversationId != m.conversationId) {
          unawaited(sb.rpc('mark_delivered', params: {'p_conversation_id': m.conversationId, 'p_up_to': m.createdAt.toIso8601String()}).then((_) {}, onError: (_) {}));
          unawaited(NotificationService.instance.showMessage(core, m));
        }
      }
    } catch (e) {
      debugPrint('realtime ingest failed: $e');
    }
  }

  // ------------------------------------------------------------------ reads
  Future<List<ChatMessage>> localPage(String conversationId, {DateTime? before, int limit = 40}) async {
    final rows = await db.messages(conversationId, beforeMs: before?.millisecondsSinceEpoch, limit: limit);
    return rows.map(fromLocal).toList();
  }

  Future<List<ChatMessage>> fetchPage(String conversationId, {DateTime? before, int limit = 40}) async {
    final rows = (await sb.rpc('get_messages', params: {
      'p_conversation_id': conversationId,
      'p_device_id': core.deviceId,
      'p_before': before?.toIso8601String(),
      'p_limit': limit,
    }) as List<dynamic>)
        .cast<Map<String, dynamic>>();
    final out = <ChatMessage>[];
    for (final r in rows) {
      out.add(await ingestRow(r));
    }
    return out;
  }

  /// Pulls everything changed since the last sync cursor.
  Future<void> sync() async {
    if (_syncing) {
      _syncAgain = true;
      return;
    }
    _syncing = true;
    try {
      do {
        _syncAgain = false;
        var cursor = await db.getKv('sync_cursor');
        if (cursor == null) {
          // Fresh install: older messages were not encrypted for this device.
          cursor = DateTime.now().toUtc().subtract(const Duration(minutes: 5)).toIso8601String();
        }
        var changed = false;
        while (true) {
          final rows = (await sb.rpc('sync_messages', params: {
            'p_device_id': core.deviceId,
            'p_since': cursor,
            'p_limit': 300,
          }) as List<dynamic>)
              .cast<Map<String, dynamic>>();
          for (final r in rows) {
            final m = await ingestRow(r);
            _events.add(ChatEvent(m.conversationId, message: m));
            changed = true;
          }
          if (rows.isNotEmpty) {
            cursor = rows.last['updated_at'] as String;
            await db.setKv('sync_cursor', cursor);
          }
          if (rows.length < 300) break;
        }
        if (changed) {
          unawaited(core.chatList.refresh());
          unawaited(sb.rpc('mark_all_delivered').then((_) {}, onError: (_) {}));
        }
      } while (_syncAgain);
    } catch (e) {
      debugPrint('sync failed: $e');
    } finally {
      _syncing = false;
    }
  }

  // ------------------------------------------------------------------ sends
  Future<String> sendText(String conversationId, String text, {Map<String, dynamic>? reply, Map<String, dynamic>? link, List<String>? mentions}) {
    return _enqueue(conversationId, 'text', {
      'v': 1,
      't': 'text',
      'text': text,
      'reply': ?reply,
      'link': ?link,
      if (mentions != null && mentions.isNotEmpty) 'mentions': mentions,
    });
  }

  Future<String> sendPayload(String conversationId, String kind, Map<String, dynamic> payload) =>
      _enqueue(conversationId, kind, {'v': 1, 't': kind, ...payload});

  /// Copies [file] into app storage so the send survives restarts, then queues it.
  Future<String> sendMedia(String conversationId, String kind, File file,
      {String? caption, String? mime, String? name, Map<String, dynamic>? extra, Map<String, dynamic>? reply, bool forwarded = false}) async {
    final size = await file.length();
    if (size > maxMediaBytes) throw MediaTooLarge(size);
    final id = _uuid.v4();
    final dir = Directory(p.join((await getApplicationSupportDirectory()).path, 'outbox'));
    await dir.create(recursive: true);
    final ext = p.extension(name ?? file.path);
    final copy = await file.copy(p.join(dir.path, '$id$ext'));
    return _enqueue(conversationId, kind, {
      'v': 1,
      't': kind,
      'text': ?caption,
      'reply': ?reply,
      if (forwarded) 'fwd': true,
      'media': {
        'mime': mime ?? _mimeFor(ext),
        'name': name ?? p.basename(file.path),
        'size': size,
        ...?extra,
      },
    }, id: id, localFile: copy.path);
  }

  Future<String> _enqueue(String conversationId, String kind, Map<String, dynamic> payload, {String? id, String? localFile}) async {
    final messageId = id ?? _uuid.v4();
    final now = DateTime.now().toUtc();
    final body = <String, dynamic>{'payload': payload, 'localFile': ?localFile};
    await db.enqueue(OutboxItem(id: messageId, conversationId: conversationId, kind: kind, body: body, createdAt: now));
    final row = LocalMessageRow(
      id: messageId,
      conversationId: conversationId,
      senderId: core.userId,
      senderDeviceId: core.deviceId,
      kind: kind,
      payload: payload,
      system: null,
      createdAt: now,
      updatedAt: now,
      localState: 1,
    );
    await db.upsertMessage(row);
    if (localFile != null) await db.saveMedia('local:$messageId', localFile, 0);
    final m = fromLocal(row);
    _events.add(ChatEvent(conversationId, message: m));
    core.chatList.onMessage(m, isNew: true);
    unawaited(flushOutbox());
    return messageId;
  }

  Future<void> retry(String messageId) async {
    final row = await db.message(messageId);
    if (row == null) return;
    final pending = await db.pending();
    if (!pending.any((o) => o.id == messageId)) {
      await db.enqueue(OutboxItem(
        id: messageId,
        conversationId: row.conversationId,
        kind: row.kind,
        body: {'payload': row.payload ?? {}, 'localFile': await db.mediaPath('local:$messageId')},
        createdAt: row.createdAt,
      ));
    }
    await _setLocalState(row, 1);
    unawaited(flushOutbox());
  }

  Future<void> _setLocalState(LocalMessageRow row, int state, {DateTime? createdAt, Map<String, dynamic>? payload}) async {
    final updated = LocalMessageRow(
      id: row.id,
      conversationId: row.conversationId,
      senderId: row.senderId,
      senderDeviceId: row.senderDeviceId,
      kind: row.kind,
      payload: payload ?? row.payload,
      system: row.system,
      createdAt: createdAt ?? row.createdAt,
      updatedAt: createdAt ?? row.updatedAt,
      editedAt: row.editedAt,
      deletedAt: row.deletedAt,
      localState: state,
    );
    await db.upsertMessage(updated);
    _events.add(ChatEvent(row.conversationId, message: fromLocal(updated)));
    core.chatList.onMessage(fromLocal(updated), isNew: false);
  }

  /// Sends queued messages in order; stops at the first network failure.
  Future<void> flushOutbox() async {
    if (_flushing) return;
    _flushing = true;
    try {
      for (final item in await db.pending()) {
        final result = await _sendItem(item);
        if (result == _SendResult.retryLater) break;
      }
    } finally {
      _flushing = false;
    }
  }

  Future<_SendResult> _sendItem(OutboxItem item) async {
    final row = await db.message(item.id);
    var payload = Map<String, dynamic>.from(item.body['payload'] as Map);
    final localFile = item.body['localFile'] as String?;
    try {
      final attachments = <Map<String, dynamic>>[];
      final media = payload['media'] is Map ? Map<String, dynamic>.from(payload['media'] as Map) : null;
      if (media != null) {
        if (media['path'] == null) {
          if (localFile == null || !File(localFile).existsSync()) throw const _Permanent('file_missing');
          final uploaded = await _uploadEncrypted(item.conversationId, item.id, File(localFile));
          media.addAll(uploaded);
          payload = {...payload, 'media': media};
          await db.enqueue(OutboxItem(
            id: item.id,
            conversationId: item.conversationId,
            kind: item.kind,
            body: {'payload': payload, 'localFile': localFile},
            createdAt: item.createdAt,
            attempts: item.attempts,
          ));
          await db.saveMedia(media['path'] as String, localFile, (media['size'] as num?)?.toInt() ?? 0);
        }
        attachments.add({'path': media['path'], 'kind': item.kind == 'image' || item.kind == 'video' || item.kind == 'voice' || item.kind == 'audio' ? item.kind : 'document'});
      }
      final created = await _sealAndSend(item.conversationId, item.id, item.kind, payload, attachments);
      await db.dequeue(item.id);
      if (row != null) await _setLocalState(row, 0, createdAt: created, payload: payload);
      unawaited(sb.functions.invoke('push', body: {'type': 'message', 'message_id': item.id}).then((_) {}, onError: (_) {}));
      return _SendResult.sent;
    } on _Permanent catch (e) {
      await db.dequeue(item.id);
      if (row != null) await _setLocalState(row, 2);
      debugPrint('send ${item.id} failed permanently: ${e.code}');
      return _SendResult.failed;
    } on PostgrestException catch (e) {
      const permanent = ['not_a_member', 'only_admins_can_send', 'you_blocked_this_contact', 'invalid_kind', 'recipient_unavailable', 'id_conflict', 'invalid_attachment'];
      if (permanent.any((k) => e.message.contains(k))) {
        await db.dequeue(item.id);
        if (row != null) await _setLocalState(row, 2);
        return _SendResult.failed;
      }
      await db.markAttempt(item.id, e.message);
      return _SendResult.retryLater;
    } catch (e) {
      await db.markAttempt(item.id, e.toString());
      if (item.attempts >= 20 && row != null) {
        await db.dequeue(item.id);
        await _setLocalState(row, 2);
        return _SendResult.failed;
      }
      return _SendResult.retryLater;
    }
  }

  Future<DateTime> _sealAndSend(String conversationId, String messageId, String kind, Map<String, dynamic> payload,
      List<Map<String, dynamic>> attachments) async {
    var refreshed = false;
    while (true) {
      final devices = await conversationDevices(conversationId, refresh: refreshed);
      final sealed = await core.e2ee.seal(
        payload: payload,
        messageId: messageId,
        conversationId: conversationId,
        senderId: core.userId,
        recipients: devices,
      );
      try {
        final res = await sb.rpc('send_message', params: {
          'p_id': messageId,
          'p_conversation_id': conversationId,
          'p_kind': kind,
          'p_ciphertext': sealed.ciphertext,
          'p_nonce': sealed.nonce,
          'p_eph_key': sealed.ephKey,
          'p_keys': sealed.keys,
          'p_device_id': core.deviceId,
          'p_attachments': attachments,
        }) as Map<String, dynamic>;
        return parseTime(res['created_at']) ?? DateTime.now().toUtc();
      } on PostgrestException catch (e) {
        if (e.message.contains('stale_devices') && !refreshed) {
          refreshed = true;
          continue;
        }
        if (e.message.contains('unknown_device') && !refreshed) {
          refreshed = true;
          await core.registerDevice();
          continue;
        }
        rethrow;
      }
    }
  }

  Future<Map<String, dynamic>> _uploadEncrypted(String conversationId, String messageId, File file) async {
    final key = MediaCrypto.randomBytes(32);
    final nonce = MediaCrypto.randomBytes(12);
    final tmp = File(p.join((await getTemporaryDirectory()).path, 'up_$messageId.enc'));
    final bar = progress.putIfAbsent(messageId, () => ValueNotifier(0));
    bar.value = 0.02;
    final encSize = await MediaCrypto.encryptFile(file, tmp, key, nonce, onProgress: (v) => bar.value = 0.02 + v * 0.18);
    final path = '$conversationId/${_uuid.v4()}';
    try {
      final signed = await sb.storage.from('media').createSignedUploadUrl(path);
      final req = _ProgressMultipart('PUT', Uri.parse(signed.signedUrl), (sent, total) {
        bar.value = 0.2 + 0.8 * (sent / (total == 0 ? 1 : total));
      });
      req.headers['x-upsert'] = 'false';
      req.fields['cacheControl'] = '3600';
      req.files.add(http.MultipartFile('', tmp.openRead(), encSize, filename: ''));
      final res = await req.send().timeout(const Duration(minutes: 10));
      final body = await res.stream.bytesToString();
      if (res.statusCode >= 300) throw HttpException('upload ${res.statusCode}: $body');
      bar.value = 1;
      return {'path': path, 'key': base64Encode(key), 'nonce': base64Encode(nonce), 'enc': encSize};
    } finally {
      if (tmp.existsSync()) await tmp.delete();
    }
  }

  // ---------------------------------------------------------------- media
  /// Local decrypted file for a media message (downloads if needed).
  Future<File?> mediaFile(ChatMessage m) async {
    final media = m.media;
    if (media == null) return null;
    final path = media['path'] as String?;
    final local = await db.mediaPath(path ?? 'local:${m.id}') ?? await db.mediaPath('local:${m.id}');
    if (local != null && File(local).existsSync()) return File(local);
    if (path == null || media['key'] == null) return null;
    final bar = progress.putIfAbsent(m.id, () => ValueNotifier(0));
    bar.value = 0.01;
    final url = await sb.storage.from('media').createSignedUrl(path, 300);
    final tmp = File(p.join((await getTemporaryDirectory()).path, 'dl_${m.id}.enc'));
    final req = await http.Client().send(http.Request('GET', Uri.parse(url)));
    if (req.statusCode >= 300) throw HttpException('download ${req.statusCode}');
    final total = req.contentLength ?? (media['enc'] as num?)?.toInt() ?? 0;
    var got = 0;
    final sink = tmp.openWrite();
    await for (final chunk in req.stream) {
      sink.add(chunk);
      got += chunk.length;
      if (total > 0) bar.value = 0.85 * got / total;
    }
    await sink.close();
    final dir = Directory(p.join((await getApplicationSupportDirectory()).path, 'media', m.conversationId));
    await dir.create(recursive: true);
    final name = (media['name'] as String?) ?? m.id;
    final out = File(p.join(dir.path, '${m.id}${p.extension(name)}'));
    try {
      await MediaCrypto.decryptFile(tmp, out, base64Decode(media['key'] as String), base64Decode(media['nonce'] as String),
          onProgress: (v) => bar.value = 0.85 + 0.15 * v);
    } finally {
      if (tmp.existsSync()) await tmp.delete();
    }
    await db.saveMedia(path, out.path, await out.length());
    bar.value = 1;
    return out;
  }

  // -------------------------------------------------------------- actions
  Future<void> editText(ChatMessage m, String text) async {
    final payload = {...?m.payload, 'text': text};
    final devices = await conversationDevices(m.conversationId, refresh: true);
    final sealed = await core.e2ee.seal(
      payload: payload,
      messageId: m.id,
      conversationId: m.conversationId,
      senderId: core.userId,
      recipients: devices,
    );
    await sb.rpc('edit_message', params: {
      'p_id': m.id,
      'p_ciphertext': sealed.ciphertext,
      'p_nonce': sealed.nonce,
      'p_eph_key': sealed.ephKey,
      'p_keys': sealed.keys,
    });
    final row = await db.message(m.id);
    if (row != null) {
      final updated = LocalMessageRow(
        id: row.id,
        conversationId: row.conversationId,
        senderId: row.senderId,
        senderDeviceId: row.senderDeviceId,
        kind: row.kind,
        payload: payload,
        system: row.system,
        createdAt: row.createdAt,
        updatedAt: DateTime.now().toUtc(),
        editedAt: DateTime.now().toUtc(),
      );
      await db.upsertMessage(updated);
      _events.add(ChatEvent(m.conversationId, message: fromLocal(updated)));
    }
  }

  Future<void> deleteForEveryone(ChatMessage m) async {
    await sb.rpc('delete_message_for_everyone', params: {'p_id': m.id});
    await sync();
  }

  Future<void> deleteForMe(ChatMessage m) async {
    if (m.localState == 0) {
      await sb.from('message_hidden').insert({'user_id': core.userId, 'message_id': m.id, 'conversation_id': m.conversationId});
    } else {
      await db.dequeue(m.id);
    }
    await db.removeMessage(m.id);
    _events.add(ChatEvent(m.conversationId, removedId: m.id));
    unawaited(core.chatList.refresh());
  }

  Future<void> react(ChatMessage m, String? emoji) async {
    if (emoji == null) {
      await sb.from('message_reactions').delete().eq('message_id', m.id).eq('user_id', core.userId);
    } else {
      // Only the emoji column may be updated, so change-or-insert instead of an upsert.
      final changed = await sb
          .from('message_reactions')
          .update({'emoji': emoji})
          .eq('message_id', m.id)
          .eq('user_id', core.userId)
          .select('message_id');
      if (changed.isEmpty) {
        await sb.from('message_reactions').insert({
          'message_id': m.id,
          'conversation_id': m.conversationId,
          'user_id': core.userId,
          'emoji': emoji,
        });
      }
    }
    await db.setReaction(m.conversationId, m.id, core.userId, emoji);
  }

  Future<Map<String, Map<String, String>>> loadReactions(String conversationId) async {
    try {
      final rows = (await sb.from('message_reactions').select('message_id, user_id, emoji').eq('conversation_id', conversationId))
          .cast<Map<String, dynamic>>();
      await db.replaceReactions(conversationId, rows);
    } catch (_) {}
    return db.reactions(conversationId);
  }

  Future<Set<String>> starredIds(String conversationId) async {
    final rows = await sb.from('message_stars').select('message_id').eq('conversation_id', conversationId);
    return rows.map((r) => r['message_id'] as String).toSet();
  }

  Future<void> setStarred(ChatMessage m, bool starred) async {
    if (starred) {
      await sb.from('message_stars').upsert({'user_id': core.userId, 'message_id': m.id, 'conversation_id': m.conversationId},
          onConflict: 'user_id,message_id', ignoreDuplicates: true);
    } else {
      await sb.from('message_stars').delete().eq('user_id', core.userId).eq('message_id', m.id);
    }
  }

  Future<List<ChatMessage>> allStarred() async {
    final rows = await sb.from('message_stars').select('message_id').order('created_at', ascending: false).limit(500);
    final out = <ChatMessage>[];
    for (final r in rows) {
      final local = await db.message(r['message_id'] as String);
      if (local != null) out.add(fromLocal(local));
    }
    return out;
  }

  Future<List<String>> pinnedIds(String conversationId) async {
    final rows = await sb
        .from('conversation_pins')
        .select('message_id')
        .eq('conversation_id', conversationId)
        .order('pinned_at', ascending: false);
    return rows.map((r) => r['message_id'] as String).toList();
  }

  Future<void> setPinned(ChatMessage m, bool pinned) async {
    if (pinned) {
      final current = await pinnedIds(m.conversationId);
      if (current.length >= 3) {
        await sb.from('conversation_pins').delete().eq('conversation_id', m.conversationId).eq('message_id', current.last);
      }
      await sb.from('conversation_pins').insert({'conversation_id': m.conversationId, 'message_id': m.id, 'pinned_by': core.userId});
    } else {
      await sb.from('conversation_pins').delete().eq('conversation_id', m.conversationId).eq('message_id', m.id);
    }
  }

  Future<void> markRead(String conversationId, DateTime upTo) async {
    try {
      await sb.rpc('mark_read', params: {'p_conversation_id': conversationId, 'p_up_to': upTo.toUtc().toIso8601String()});
    } catch (_) {}
  }

  Future<void> clearChat(String conversationId) async {
    await sb
        .from('conversation_member_state')
        .update({'cleared_at': DateTime.now().toUtc().toIso8601String()})
        .eq('conversation_id', conversationId)
        .eq('user_id', core.userId);
    await db.clearConversation(conversationId);
    _events.add(ChatEvent(conversationId, reload: true));
    unawaited(core.chatList.refresh());
  }

  /// Decrypted local messages matching [query] (search never leaves the phone).
  Future<List<ChatMessage>> search(String query, {String? conversationId}) async {
    final q = query.trim().toLowerCase();
    if (q.isEmpty) return [];
    final rows = await db.recent(conversationId: conversationId);
    return rows
        .where((r) {
          final payload = r.payload;
          if (payload == null) return false;
          final text = '${payload['text'] ?? ''} ${(payload['media'] as Map?)?['name'] ?? ''}'.toLowerCase();
          return text.contains(q);
        })
        .map(fromLocal)
        .take(200)
        .toList();
  }

  Future<List<ChatMessage>> mediaMessages({String? conversationId, List<String> kinds = const ['image', 'video']}) async {
    final rows = await db.recent(conversationId: conversationId, kinds: kinds, limit: 600);
    return rows.where((r) => r.payload != null).map(fromLocal).toList();
  }

  static String _mimeFor(String ext) {
    switch (ext.toLowerCase()) {
      case '.jpg':
      case '.jpeg':
        return 'image/jpeg';
      case '.png':
        return 'image/png';
      case '.webp':
        return 'image/webp';
      case '.gif':
        return 'image/gif';
      case '.mp4':
        return 'video/mp4';
      case '.3gp':
        return 'video/3gpp';
      case '.mov':
        return 'video/quicktime';
      case '.m4a':
        return 'audio/mp4';
      case '.aac':
        return 'audio/aac';
      case '.mp3':
        return 'audio/mpeg';
      case '.pdf':
        return 'application/pdf';
      case '.doc':
        return 'application/msword';
      case '.docx':
        return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
      case '.xlsx':
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
      case '.pptx':
        return 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
      case '.txt':
        return 'text/plain';
      case '.zip':
        return 'application/zip';
      default:
        return 'application/octet-stream';
    }
  }
}

enum _SendResult { sent, failed, retryLater }

class _Permanent implements Exception {
  const _Permanent(this.code);
  final String code;
}

class MediaTooLarge implements UserFacingException {
  MediaTooLarge(this.size);
  final int size;
  @override
  String toString() => 'Files up to ${Fmt.bytes(ChatRepository.maxMediaBytes)} can be sent (this one is ${Fmt.bytes(size)}).';
}

/// Multipart request that reports real bytes handed to the network.
class _ProgressMultipart extends http.MultipartRequest {
  _ProgressMultipart(super.method, super.url, this.onProgress);
  final void Function(int sent, int total) onProgress;

  @override
  http.ByteStream finalize() {
    final stream = super.finalize();
    final total = contentLength;
    var sent = 0;
    return http.ByteStream(stream.transform(StreamTransformer<List<int>, List<int>>.fromHandlers(handleData: (data, sink) {
      sent += data.length;
      onProgress(sent, total);
      sink.add(data);
    })));
  }
}
