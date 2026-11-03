import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../features/calls/call_controller.dart';
import '../features/chats/chat_list_controller.dart';
import '../features/chats/chat_repository.dart';
import '../features/chats/models.dart';
import 'e2ee.dart';
import 'local_db.dart';
import 'notifications.dart';

/// Everything that exists only while a user is signed in on this device:
/// keys, the local database, realtime connection, repositories and the call
/// engine. Created by [SessionController] after login, disposed on logout.
class HimeCore {
  HimeCore._(this.sb, this.userId, this.e2ee, this.db);

  final SupabaseClient sb;
  final String userId;
  final E2ee e2ee;
  final LocalDb db;

  String get deviceId => e2ee.deviceId;

  late final ProfileStore profiles = ProfileStore(this);
  late final ChatRepository chats = ChatRepository(this);
  late final ChatListController chatList = ChatListController(this);
  late final RealtimeHub realtime = RealtimeHub(this);
  late final PresenceService presence = PresenceService(this);
  late final CallController calls = CallController(this);

  final online = ValueNotifier<bool>(true);

  /// Conversation currently on screen (no notifications for it, auto read).
  String? openConversationId;

  StreamSubscription<List<ConnectivityResult>>? _connSub;
  Timer? _syncTimer;
  bool _disposed = false;

  static Future<HimeCore> create(SupabaseClient sb, String userId) async {
    final e2ee = await E2ee.load(userId);
    final vault = await LocalVault.load(userId);
    final db = await LocalDb.open(userId, vault);
    final core = HimeCore._(sb, userId, e2ee, db);
    await core.registerDevice();
    return core;
  }

  /// Registers (or refreshes) this installation and its public identity key.
  Future<void> registerDevice() async {
    var name = 'Android phone';
    var version = '';
    try {
      final info = await DeviceInfoPlugin().androidInfo;
      final brand = info.manufacturer.isEmpty ? '' : '${info.manufacturer[0].toUpperCase()}${info.manufacturer.substring(1)} ';
      name = '$brand${info.model}'.trim();
    } catch (_) {}
    try {
      final pkg = await PackageInfo.fromPlatform();
      version = '${pkg.version}+${pkg.buildNumber}';
    } catch (_) {}
    final id = await sb.rpc('register_device', params: {
      'p_identity_key': e2ee.publicKeyB64,
      'p_name': name,
      'p_platform': 'android',
      'p_app_version': version,
    });
    await E2ee.saveDeviceId(userId, e2ee, id as String);
  }

  Future<void> start() async {
    final initial = await Connectivity().checkConnectivity();
    online.value = !initial.contains(ConnectivityResult.none) || initial.isEmpty;
    _connSub = Connectivity().onConnectivityChanged.listen((r) {
      final now = !r.contains(ConnectivityResult.none);
      if (now && !online.value) {
        unawaited(chats.sync());
        unawaited(chats.flushOutbox());
        unawaited(chatList.refresh());
      }
      online.value = now;
    });
    await chatList.loadCached();
    realtime.start();
    presence.start();
    unawaited(chatList.refresh());
    unawaited(chats.sync().then((_) => chats.flushOutbox()));
    unawaited(NotificationService.instance.registerPushToken(this));
    // Safety net in case a realtime event is missed while the app is open.
    _syncTimer = Timer.periodic(const Duration(seconds: 45), (_) {
      if (online.value && !_disposed) unawaited(chats.sync());
    });
  }

  void onResumed() {
    presence.goOnline();
    unawaited(chats.sync().then((_) => chats.flushOutbox()));
    unawaited(chatList.refresh());
    unawaited(calls.checkIncoming());
  }

  void onPaused() => presence.goOffline();

  Future<void> dispose() async {
    _disposed = true;
    _syncTimer?.cancel();
    await _connSub?.cancel();
    await calls.endIfActive();
    presence.stop();
    await realtime.stop();
    chatList.dispose();
    await db.close();
  }
}

/// Listens on the private "user:<id>" topic for database-sent events.
class RealtimeHub {
  RealtimeHub(this.core);
  final HimeCore core;

  RealtimeChannel? _channel;
  final connected = ValueNotifier<bool>(false);
  Timer? _retry;
  int _attempt = 0;
  bool _stopped = false;

  final _message = StreamController<Map<String, dynamic>>.broadcast();
  final _receipt = StreamController<Map<String, dynamic>>.broadcast();
  final _reaction = StreamController<Map<String, dynamic>>.broadcast();
  final _conversation = StreamController<Map<String, dynamic>>.broadcast();
  final _pins = StreamController<Map<String, dynamic>>.broadcast();
  final _call = StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get receipts => _receipt.stream;
  Stream<Map<String, dynamic>> get reactions => _reaction.stream;
  Stream<Map<String, dynamic>> get conversations => _conversation.stream;
  Stream<Map<String, dynamic>> get pins => _pins.stream;
  Stream<Map<String, dynamic>> get calls => _call.stream;
  Stream<Map<String, dynamic>> get rawMessages => _message.stream;

  static Map<String, dynamic> _unwrap(Map<String, dynamic> raw) {
    final inner = raw['payload'];
    if (inner is Map) return Map<String, dynamic>.from(inner);
    return raw;
  }

  void start() {
    _stopped = false;
    _subscribe();
  }

  void _subscribe() {
    if (_stopped) return;
    final sb = core.sb;
    final ch = sb.channel('user:${core.userId}', opts: const RealtimeChannelConfig(private: true));
    ch
        .onBroadcast(event: 'message', callback: (p) {
          final data = _unwrap(p);
          _message.add(data);
          unawaited(core.chats.ingestRealtime(data));
        })
        .onBroadcast(event: 'receipt', callback: (p) => _receipt.add(_unwrap(p)))
        .onBroadcast(event: 'reaction', callback: (p) => _reaction.add(_unwrap(p)))
        .onBroadcast(event: 'conversation', callback: (p) => _conversation.add(_unwrap(p)))
        .onBroadcast(event: 'pins', callback: (p) => _pins.add(_unwrap(p)))
        .onBroadcast(event: 'call', callback: (p) => _call.add(_unwrap(p)))
        .subscribe((status, error) {
      if (status == RealtimeSubscribeStatus.subscribed) {
        _attempt = 0;
        connected.value = true;
        unawaited(core.chats.sync());
      } else if (status == RealtimeSubscribeStatus.channelError || status == RealtimeSubscribeStatus.timedOut) {
        connected.value = false;
        _scheduleRetry();
      } else if (status == RealtimeSubscribeStatus.closed) {
        connected.value = false;
      }
    });
    _channel = ch;
  }

  void _scheduleRetry() {
    if (_stopped) return;
    _retry?.cancel();
    final secs = [2, 4, 8, 15, 30][_attempt.clamp(0, 4)];
    _attempt++;
    _retry = Timer(Duration(seconds: secs), () async {
      final old = _channel;
      _channel = null;
      if (old != null) await core.sb.removeChannel(old);
      _subscribe();
    });
  }

  Future<void> stop() async {
    _stopped = true;
    _retry?.cancel();
    final ch = _channel;
    _channel = null;
    if (ch != null) await core.sb.removeChannel(ch);
    connected.value = false;
  }
}

class PresenceInfo {
  const PresenceInfo({this.online = false, this.lastSeen});
  final bool online;
  final DateTime? lastSeen;
}

/// Own online state (tracked on "presence:<me>") plus watching others.
class PresenceService {
  PresenceService(this.core);
  final HimeCore core;

  RealtimeChannel? _own;
  Timer? _heartbeat;
  final _watched = <String, _Watch>{};

  void start() => goOnline();

  void goOnline() {
    _heartbeat?.cancel();
    unawaited(_beat());
    _heartbeat = Timer.periodic(const Duration(seconds: 40), (_) => _beat());
    if (_own == null) {
      final ch = core.sb.channel('presence:${core.userId}', opts: const RealtimeChannelConfig(private: true, key: 'self'));
      ch.subscribe((status, _) async {
        if (status == RealtimeSubscribeStatus.subscribed) {
          await ch.track({'at': DateTime.now().toUtc().toIso8601String()});
        }
      });
      _own = ch;
    }
    for (final w in _watched.values) {
      w.resume();
    }
  }

  Future<void> _beat() async {
    try {
      await core.sb.rpc('heartbeat', params: {'p_device_id': core.deviceId});
    } catch (_) {}
  }

  void goOffline() {
    _heartbeat?.cancel();
    unawaited(_beat());
    final ch = _own;
    _own = null;
    if (ch != null) unawaited(core.sb.removeChannel(ch));
    for (final w in _watched.values) {
      w.pause();
    }
  }

  void stop() {
    goOffline();
    for (final w in _watched.values) {
      w.dispose();
    }
    _watched.clear();
  }

  /// Live online/last-seen for [userId]. Call [unwatch] when done.
  ValueNotifier<PresenceInfo> watch(String userId) {
    final w = _watched.putIfAbsent(userId, () => _Watch(core, userId));
    w.refs++;
    return w.value;
  }

  void unwatch(String userId) {
    final w = _watched[userId];
    if (w == null) return;
    w.refs--;
    if (w.refs <= 0) {
      w.dispose();
      _watched.remove(userId);
    }
  }

  /// One-off batch lookup for list screens.
  Future<Map<String, PresenceInfo>> lookup(List<String> ids) async {
    if (ids.isEmpty) return {};
    try {
      final rows = await core.sb.rpc('get_presence', params: {'p_user_ids': ids}) as List<dynamic>;
      return {
        for (final r in rows.cast<Map<String, dynamic>>())
          r['user_id'] as String: PresenceInfo(online: r['online'] == true, lastSeen: DateTime.tryParse('${r['last_seen_at']}')),
      };
    } catch (_) {
      return {};
    }
  }
}

class _Watch {
  _Watch(this.core, this.userId) {
    resume();
  }

  final HimeCore core;
  final String userId;
  int refs = 0;
  final value = ValueNotifier<PresenceInfo>(const PresenceInfo());
  RealtimeChannel? _ch;
  Timer? _poll;
  bool _live = false;

  void resume() {
    _refresh();
    _poll?.cancel();
    _poll = Timer.periodic(const Duration(seconds: 30), (_) => _refresh());
    if (_ch != null) return;
    final ch = core.sb.channel('presence:$userId', opts: const RealtimeChannelConfig(private: true));
    void sync([_]) {
      _live = ch.presenceState().isNotEmpty;
      if (_live != value.value.online) {
        value.value = PresenceInfo(online: _live, lastSeen: _live ? null : DateTime.now().toUtc());
        if (!_live) _refresh();
      }
    }

    ch.onPresenceSync(sync).onPresenceJoin(sync).onPresenceLeave(sync).subscribe();
    _ch = ch;
  }

  Future<void> _refresh() async {
    final r = await core.presence.lookup([userId]);
    final info = r[userId];
    if (info == null) return;
    value.value = PresenceInfo(online: _live || info.online, lastSeen: info.lastSeen);
  }

  void pause() {
    _poll?.cancel();
    final ch = _ch;
    _ch = null;
    if (ch != null) unawaited(core.sb.removeChannel(ch));
  }

  void dispose() {
    pause();
    value.dispose();
  }
}

/// Cache of other people's (privacy-masked) profiles.
class ProfileStore extends ChangeNotifier {
  ProfileStore(this.core);
  final HimeCore core;
  final _cache = <String, Profile>{};
  final _pending = <String>{};
  Timer? _batch;
  final _waiters = <Completer<void>>[];

  Profile? cached(String? id) => id == null ? null : _cache[id];

  String nameOf(String? id, {String fallback = 'Someone'}) {
    if (id == null) return fallback;
    if (id == core.userId) return 'You';
    final p = _cache[id];
    if (p == null) {
      unawaited(ensure([id]));
      return fallback;
    }
    return p.name;
  }

  Future<void> ensure(Iterable<String?> ids, {bool force = false}) {
    final missing = ids.whereType<String>().where((id) => force || !_cache.containsKey(id)).toSet();
    if (missing.isEmpty) return Future.value();
    _pending.addAll(missing);
    final c = Completer<void>();
    _waiters.add(c);
    _batch ??= Timer(const Duration(milliseconds: 40), _flush);
    return c.future;
  }

  Future<void> _flush() async {
    _batch = null;
    final ids = _pending.toList();
    _pending.clear();
    final waiters = List.of(_waiters);
    _waiters.clear();
    try {
      final rows = await core.sb.rpc('get_profiles', params: {'p_ids': ids}) as List<dynamic>;
      for (final r in rows.cast<Map<String, dynamic>>()) {
        final p = Profile.fromJson(r);
        _cache[p.id] = p;
      }
      notifyListeners();
    } catch (e) {
      debugPrint('profiles: $e');
    }
    for (final w in waiters) {
      if (!w.isCompleted) w.complete();
    }
  }

  Future<Profile?> fetch(String id) async {
    await ensure([id], force: true);
    return _cache[id];
  }

  void put(Profile p) {
    _cache[p.id] = p;
    notifyListeners();
  }
}

/// Lifecycle observer forwarding foreground/background to the core.
class CoreLifecycle with WidgetsBindingObserver {
  CoreLifecycle(this.core);
  final HimeCore core;

  void attach() => WidgetsBinding.instance.addObserver(this);
  void detach() => WidgetsBinding.instance.removeObserver(this);

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      core.onResumed();
    } else if (state == AppLifecycleState.paused) {
      core.onPaused();
    }
  }
}
