import 'dart:async';
import 'dart:convert';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/config.dart';
import '../features/chats/models.dart';
import 'core.dart';

const _channelMessages = AndroidNotificationChannel(
  'hime_messages',
  'Messages',
  description: 'New chat and group messages',
  importance: Importance.high,
);

const _channelCalls = AndroidNotificationChannel(
  'hime_calls',
  'Incoming calls',
  description: 'Ringing voice and video calls',
  importance: Importance.max,
  audioAttributesUsage: AudioAttributesUsage.notificationRingtone,
);

const _channelMissed = AndroidNotificationChannel(
  'hime_missed_calls',
  'Missed calls',
  description: 'Calls you did not answer',
  importance: Importance.high,
);

FirebaseOptions? _firebaseOptions() {
  final f = AppConfig.instance.firebase;
  if (f == null) return null;
  return FirebaseOptions(
    apiKey: f['apiKey']!,
    appId: f['appId']!,
    messagingSenderId: f['messagingSenderId']!,
    projectId: f['projectId']!,
    storageBucket: f['storageBucket'],
  );
}

/// FCM entry point when the app is in the background or closed. Pushes are
/// data-only and never contain message text (it is end-to-end encrypted).
@pragma('vm:entry-point')
Future<void> himeBackgroundPush(RemoteMessage message) async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppConfig.load();
  final options = _firebaseOptions();
  if (options != null && Firebase.apps.isEmpty) await Firebase.initializeApp(options: options);
  await NotificationService.instance.init(handleTaps: false);
  await NotificationService.instance.showFromPush(message.data);
}

class NotificationService {
  NotificationService._();
  static final instance = NotificationService._();

  final _plugin = FlutterLocalNotificationsPlugin();
  bool _ready = false;
  bool _pushReady = false;

  /// Route requested by tapping a notification (consumed by the app shell).
  final pendingRoute = ValueNotifier<String?>(null);

  /// Show message text in notifications (local, per device).
  bool showPreviews = true;

  Future<void> init({bool handleTaps = true}) async {
    if (_ready) return;
    await _plugin.initialize(
      settings: const InitializationSettings(android: AndroidInitializationSettings('ic_stat_hime')),
      onDidReceiveNotificationResponse: handleTaps ? _onTap : null,
    );
    final android = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    await android?.createNotificationChannel(_channelMessages);
    await android?.createNotificationChannel(_channelCalls);
    await android?.createNotificationChannel(_channelMissed);
    try {
      showPreviews = (await SharedPreferences.getInstance()).getBool('notif_previews') ?? true;
    } catch (_) {}
    if (handleTaps) {
      final launch = await _plugin.getNotificationAppLaunchDetails();
      final payload = launch?.notificationResponse?.payload;
      if (launch?.didNotificationLaunchApp == true && payload != null) _route(payload);
    }
    _ready = true;
  }

  void _onTap(NotificationResponse r) {
    final p = r.payload;
    if (p != null) _route(p);
  }

  void _route(String payload) {
    try {
      final data = jsonDecode(payload) as Map<String, dynamic>;
      switch (data['type']) {
        case 'message':
          pendingRoute.value = '/chat/${data['conversation_id']}';
        case 'call':
          pendingRoute.value = '/call';
        case 'missed_call':
          pendingRoute.value = '/calls';
      }
    } catch (_) {}
  }

  Future<void> setPreviews(bool v) async {
    showPreviews = v;
    (await SharedPreferences.getInstance()).setBool('notif_previews', v);
  }

  Future<void> requestPermission() async {
    final android = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    await android?.requestNotificationsPermission();
  }

  int _idFor(String key) => key.hashCode & 0x7fffffff;

  /// Local notification for a message that arrived over realtime.
  Future<void> showMessage(HimeCore core, ChatMessage m) async {
    if (!_ready || m.isSystem) return;
    final chat = core.chatList.byId(m.conversationId);
    if (chat != null && chat.isMuted) return;
    final sender = core.profiles.nameOf(m.senderId);
    final title = chat == null ? sender : (chat.isGroup ? chat.title : sender);
    var body = showPreviews ? m.preview() : 'New message';
    if (chat != null && chat.isGroup && showPreviews) body = '$sender: $body';
    await _plugin.show(
      id: _idFor(m.conversationId),
      title: title,
      body: body,
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          _channelMessages.id,
          _channelMessages.name,
          channelDescription: _channelMessages.description,
          importance: Importance.high,
          priority: Priority.high,
          category: AndroidNotificationCategory.message,
          color: const Color(0xFFF5D547),
          groupKey: 'hime.messages',
        ),
      ),
      payload: jsonEncode({'type': 'message', 'conversation_id': m.conversationId}),
    );
  }

  Future<void> clearChat(String conversationId) => _plugin.cancel(id: _idFor(conversationId));

  Future<void> showIncomingCall({required String callId, required String caller, required bool video}) async {
    if (!_ready) return;
    await _plugin.show(
      id: _idFor('call:$callId'),
      title: caller,
      body: video ? 'Incoming video call' : 'Incoming voice call',
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          _channelCalls.id,
          _channelCalls.name,
          channelDescription: _channelCalls.description,
          importance: Importance.max,
          priority: Priority.max,
          category: AndroidNotificationCategory.call,
          fullScreenIntent: true,
          ongoing: true,
          autoCancel: false,
          timeoutAfter: 60000,
          color: const Color(0xFFF5D547),
        ),
      ),
      payload: jsonEncode({'type': 'call', 'call_id': callId}),
    );
  }

  Future<void> cancelCall(String callId) => _plugin.cancel(id: _idFor('call:$callId'));

  Future<void> showMissedCall({required String caller, required bool video}) async {
    if (!_ready) return;
    await _plugin.show(
      id: _idFor('missed:${DateTime.now().millisecondsSinceEpoch}'),
      title: caller,
      body: video ? 'Missed video call' : 'Missed voice call',
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          _channelMissed.id,
          _channelMissed.name,
          channelDescription: _channelMissed.description,
          importance: Importance.high,
          priority: Priority.high,
          category: AndroidNotificationCategory.missedCall,
          color: const Color(0xFFF5D547),
        ),
      ),
      payload: jsonEncode({'type': 'missed_call'}),
    );
  }

  /// Displays a data push (background isolate or foreground).
  Future<void> showFromPush(Map<String, dynamic> data) async {
    final type = data['type'];
    final title = '${data['title'] ?? 'Hime'}';
    final body = '${data['body'] ?? 'New message'}';
    if (type == 'call') {
      await showIncomingCall(callId: '${data['call_id']}', caller: title, video: data['media'] == 'video');
    } else if (type == 'missed_call') {
      if (data['call_id'] != null) await cancelCall('${data['call_id']}');
      await showMissedCall(caller: title, video: data['media'] == 'video');
    } else if (type == 'message') {
      final conv = '${data['conversation_id']}';
      await _plugin.show(
        id: _idFor(conv),
        title: title,
        body: body,
        notificationDetails: NotificationDetails(
          android: AndroidNotificationDetails(
            _channelMessages.id,
            _channelMessages.name,
            channelDescription: _channelMessages.description,
            importance: Importance.high,
            priority: Priority.high,
            category: AndroidNotificationCategory.message,
            color: const Color(0xFFF5D547),
          ),
        ),
        payload: jsonEncode({'type': 'message', 'conversation_id': conv}),
      );
    }
  }

  /// Sets up Firebase Cloud Messaging when the project is configured for it.
  Future<void> registerPushToken(HimeCore core) async {
    final options = _firebaseOptions();
    if (options == null) return;
    try {
      if (Firebase.apps.isEmpty) await Firebase.initializeApp(options: options);
      if (!_pushReady) {
        FirebaseMessaging.onBackgroundMessage(himeBackgroundPush);
        FirebaseMessaging.onMessageOpenedApp.listen((m) => _route(jsonEncode(m.data)));
        _pushReady = true;
      }
      await FirebaseMessaging.instance.requestPermission();
      final token = await FirebaseMessaging.instance.getToken();
      if (token != null) {
        await core.sb.rpc('register_push_token', params: {'p_token': token, 'p_device_id': core.deviceId, 'p_platform': 'android'});
      }
      FirebaseMessaging.instance.onTokenRefresh.listen((t) {
        core.sb.rpc('register_push_token', params: {'p_token': t, 'p_device_id': core.deviceId, 'p_platform': 'android'});
      });
    } catch (e) {
      debugPrint('push setup failed: $e');
    }
  }

  Future<void> unregisterPush() async {
    if (_firebaseOptions() == null || Firebase.apps.isEmpty) return;
    try {
      await FirebaseMessaging.instance.deleteToken();
    } catch (_) {}
  }
}
