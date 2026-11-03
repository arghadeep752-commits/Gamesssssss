import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

import 'e2ee.dart';

/// On-device cache and offline queue, one database per signed-in account.
/// Message payloads are stored encrypted with the account's [LocalVault] key.
class LocalDb {
  LocalDb._(this.db, this.vault);
  final Database db;
  final LocalVault vault;

  static Future<LocalDb> open(String userId, LocalVault vault) async {
    final dir = await getDatabasesPath();
    final db = await openDatabase(
      p.join(dir, 'hime_$userId.db'),
      version: 1,
      onConfigure: (db) async => db.execute('PRAGMA journal_mode=WAL'),
      onCreate: (db, _) async {
        final batch = db.batch();
        batch.execute('''
          create table messages (
            id text primary key,
            conversation_id text not null,
            sender_id text,
            sender_device_id text,
            kind text not null,
            payload blob,
            system text,
            created_at integer not null,
            updated_at integer not null,
            edited_at integer,
            deleted_at integer,
            local_state integer not null default 0,
            undecryptable integer not null default 0
          )''');
        batch.execute('create index messages_conv_created on messages(conversation_id, created_at)');
        batch.execute('''
          create table outbox (
            id text primary key,
            conversation_id text not null,
            kind text not null,
            body blob not null,
            attempts integer not null default 0,
            created_at integer not null,
            last_error text
          )''');
        batch.execute('create table kv (key text primary key, value text)');
        batch.execute('create table media (path text primary key, local_path text not null, size integer, created_at integer)');
        batch.execute('create table devices (device_id text primary key, user_id text not null, identity_key text not null, first_seen integer)');
        batch.execute('''
          create table reactions (
            message_id text not null, user_id text not null, conversation_id text not null, emoji text not null,
            primary key (message_id, user_id))''');
        await batch.commit(noResult: true);
      },
    );
    return LocalDb._(db, vault);
  }

  Future<void> close() => db.close();

  // ---- key/value ----
  Future<String?> getKv(String key) async {
    final r = await db.query('kv', where: 'key = ?', whereArgs: [key], limit: 1);
    return r.isEmpty ? null : r.first['value'] as String?;
  }

  Future<void> setKv(String key, String value) =>
      db.insert('kv', {'key': key, 'value': value}, conflictAlgorithm: ConflictAlgorithm.replace);

  // ---- devices (known identity keys) ----
  Future<void> rememberDevices(List<Map<String, dynamic>> rows) async {
    final batch = db.batch();
    for (final r in rows) {
      batch.insert(
        'devices',
        {
          'device_id': r['device_id'],
          'user_id': r['user_id'],
          'identity_key': r['identity_key'],
          'first_seen': DateTime.now().millisecondsSinceEpoch,
        },
        conflictAlgorithm: ConflictAlgorithm.ignore,
      );
    }
    await batch.commit(noResult: true);
  }

  Future<String?> deviceKey(String deviceId) async {
    final r = await db.query('devices', columns: ['identity_key'], where: 'device_id = ?', whereArgs: [deviceId], limit: 1);
    return r.isEmpty ? null : r.first['identity_key'] as String;
  }

  Future<List<Map<String, Object?>>> devicesOf(String userId) =>
      db.query('devices', where: 'user_id = ?', whereArgs: [userId]);

  // ---- messages ----
  Future<void> upsertMessage(LocalMessageRow m) async {
    await db.insert('messages', await m.toRow(vault), conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<LocalMessageRow>> messages(String conversationId, {int? beforeMs, int limit = 50}) async {
    final rows = await db.query(
      'messages',
      where: beforeMs == null ? 'conversation_id = ?' : 'conversation_id = ? and created_at < ?',
      whereArgs: beforeMs == null ? [conversationId] : [conversationId, beforeMs],
      orderBy: 'created_at desc',
      limit: limit,
    );
    return Future.wait(rows.map((r) => LocalMessageRow.fromRow(r, vault)));
  }

  Future<LocalMessageRow?> message(String id) async {
    final rows = await db.query('messages', where: 'id = ?', whereArgs: [id], limit: 1);
    if (rows.isEmpty) return null;
    return LocalMessageRow.fromRow(rows.first, vault);
  }

  Future<void> removeMessage(String id) => db.delete('messages', where: 'id = ?', whereArgs: [id]);

  Future<void> clearConversation(String conversationId) =>
      db.delete('messages', where: 'conversation_id = ?', whereArgs: [conversationId]);

  /// Recent messages for search/media views (decrypted in memory only).
  Future<List<LocalMessageRow>> recent({String? conversationId, List<String>? kinds, int limit = 4000}) async {
    final where = <String>[];
    final args = <Object?>[];
    if (conversationId != null) {
      where.add('conversation_id = ?');
      args.add(conversationId);
    }
    if (kinds != null && kinds.isNotEmpty) {
      where.add('kind in (${List.filled(kinds.length, '?').join(',')})');
      args.addAll(kinds);
    }
    where.add('deleted_at is null');
    final rows = await db.query('messages',
        where: where.join(' and '), whereArgs: args, orderBy: 'created_at desc', limit: limit);
    return Future.wait(rows.map((r) => LocalMessageRow.fromRow(r, vault)));
  }

  // ---- outbox ----
  Future<void> enqueue(OutboxItem item) async =>
      db.insert('outbox', await item.toRow(vault), conflictAlgorithm: ConflictAlgorithm.replace);

  Future<List<OutboxItem>> pending() async {
    final rows = await db.query('outbox', orderBy: 'created_at asc');
    return Future.wait(rows.map((r) => OutboxItem.fromRow(r, vault)));
  }

  Future<void> dequeue(String id) => db.delete('outbox', where: 'id = ?', whereArgs: [id]);

  Future<void> markAttempt(String id, String error) => db.rawUpdate(
      'update outbox set attempts = attempts + 1, last_error = ? where id = ?', [error, id]);

  // ---- media cache ----
  Future<String?> mediaPath(String remotePath) async {
    final r = await db.query('media', where: 'path = ?', whereArgs: [remotePath], limit: 1);
    return r.isEmpty ? null : r.first['local_path'] as String;
  }

  Future<void> saveMedia(String remotePath, String localPath, int size) => db.insert(
      'media',
      {'path': remotePath, 'local_path': localPath, 'size': size, 'created_at': DateTime.now().millisecondsSinceEpoch},
      conflictAlgorithm: ConflictAlgorithm.replace);

  Future<List<Map<String, Object?>>> allMedia() => db.query('media');

  Future<void> clearMediaIndex() => db.delete('media');

  // ---- reactions ----
  Future<void> setReaction(String conversationId, String messageId, String userId, String? emoji) async {
    if (emoji == null) {
      await db.delete('reactions', where: 'message_id = ? and user_id = ?', whereArgs: [messageId, userId]);
    } else {
      await db.insert('reactions',
          {'message_id': messageId, 'user_id': userId, 'conversation_id': conversationId, 'emoji': emoji},
          conflictAlgorithm: ConflictAlgorithm.replace);
    }
  }

  Future<Map<String, Map<String, String>>> reactions(String conversationId) async {
    final rows = await db.query('reactions', where: 'conversation_id = ?', whereArgs: [conversationId]);
    final out = <String, Map<String, String>>{};
    for (final r in rows) {
      (out[r['message_id'] as String] ??= {})[r['user_id'] as String] = r['emoji'] as String;
    }
    return out;
  }

  Future<void> replaceReactions(String conversationId, List<Map<String, dynamic>> rows) async {
    await db.transaction((txn) async {
      await txn.delete('reactions', where: 'conversation_id = ?', whereArgs: [conversationId]);
      for (final r in rows) {
        await txn.insert('reactions', {
          'message_id': r['message_id'],
          'user_id': r['user_id'],
          'conversation_id': conversationId,
          'emoji': r['emoji'],
        });
      }
    });
  }
}

/// A message as cached on the device.
class LocalMessageRow {
  LocalMessageRow({
    required this.id,
    required this.conversationId,
    required this.senderId,
    required this.senderDeviceId,
    required this.kind,
    required this.payload,
    required this.system,
    required this.createdAt,
    required this.updatedAt,
    this.editedAt,
    this.deletedAt,
    this.localState = 0,
    this.undecryptable = false,
  });

  final String id;
  final String conversationId;
  final String? senderId;
  final String? senderDeviceId;
  final String kind;
  final Map<String, dynamic>? payload;
  final Map<String, dynamic>? system;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? editedAt;
  final DateTime? deletedAt;

  /// 0 = stored on server, 1 = waiting in outbox, 2 = failed.
  final int localState;
  final bool undecryptable;

  Future<Map<String, Object?>> toRow(LocalVault vault) async => {
        'id': id,
        'conversation_id': conversationId,
        'sender_id': senderId,
        'sender_device_id': senderDeviceId,
        'kind': kind,
        'payload': payload == null ? null : await vault.seal(jsonEncode(payload)),
        'system': system == null ? null : jsonEncode(system),
        'created_at': createdAt.millisecondsSinceEpoch,
        'updated_at': updatedAt.millisecondsSinceEpoch,
        'edited_at': editedAt?.millisecondsSinceEpoch,
        'deleted_at': deletedAt?.millisecondsSinceEpoch,
        'local_state': localState,
        'undecryptable': undecryptable ? 1 : 0,
      };

  static Future<LocalMessageRow> fromRow(Map<String, Object?> r, LocalVault vault) async {
    Map<String, dynamic>? payload;
    final blob = r['payload'];
    if (blob is List<int>) {
      try {
        payload = jsonDecode(await vault.open(blob)) as Map<String, dynamic>;
      } catch (_) {}
    }
    DateTime? t(Object? v) => v == null ? null : DateTime.fromMillisecondsSinceEpoch(v as int, isUtc: true);
    return LocalMessageRow(
      id: r['id'] as String,
      conversationId: r['conversation_id'] as String,
      senderId: r['sender_id'] as String?,
      senderDeviceId: r['sender_device_id'] as String?,
      kind: r['kind'] as String,
      payload: payload,
      system: r['system'] == null ? null : jsonDecode(r['system'] as String) as Map<String, dynamic>,
      createdAt: t(r['created_at'])!,
      updatedAt: t(r['updated_at'])!,
      editedAt: t(r['edited_at']),
      deletedAt: t(r['deleted_at']),
      localState: (r['local_state'] as int?) ?? 0,
      undecryptable: (r['undecryptable'] as int?) == 1,
    );
  }
}

/// A message waiting to be encrypted and sent (survives restarts).
class OutboxItem {
  OutboxItem({
    required this.id,
    required this.conversationId,
    required this.kind,
    required this.body,
    required this.createdAt,
    this.attempts = 0,
    this.lastError,
  });

  final String id;
  final String conversationId;
  final String kind;

  /// {payload: {...}, localFile: path?, attachmentKind: ...}
  final Map<String, dynamic> body;
  final DateTime createdAt;
  final int attempts;
  final String? lastError;

  Future<Map<String, Object?>> toRow(LocalVault vault) async => {
        'id': id,
        'conversation_id': conversationId,
        'kind': kind,
        'body': await vault.seal(jsonEncode(body)),
        'attempts': attempts,
        'created_at': createdAt.millisecondsSinceEpoch,
        'last_error': lastError,
      };

  static Future<OutboxItem> fromRow(Map<String, Object?> r, LocalVault vault) async => OutboxItem(
        id: r['id'] as String,
        conversationId: r['conversation_id'] as String,
        kind: r['kind'] as String,
        body: jsonDecode(await vault.open(r['body'] as List<int>)) as Map<String, dynamic>,
        createdAt: DateTime.fromMillisecondsSinceEpoch(r['created_at'] as int, isUtc: true),
        attempts: (r['attempts'] as int?) ?? 0,
        lastError: r['last_error'] as String?,
      );
}
