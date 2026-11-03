import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:just_audio/just_audio.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import '../../services/core.dart';
import '../../services/notifications.dart';

enum CallPhase { idle, outgoing, incoming, connecting, active, reconnecting, ended }

/// One-to-one WebRTC calls. Signalling (offer/answer/ICE) travels over a
/// private realtime topic "call:<id>" that only the two participants can
/// join; the call record and its lifecycle live in the database.
class CallController extends ChangeNotifier {
  CallController(this.core) {
    _sub = core.realtime.calls.listen(_onCallEvent);
    native.setMethodCallHandler((call) async {
      if (call.method == 'pipChanged') {
        inPip = call.arguments == true;
        notifyListeners();
      }
      return null;
    });
  }

  final HimeCore core;
  static const native = MethodChannel('app.hime/native');
  SupabaseClient get sb => core.sb;
  StreamSubscription<Map<String, dynamic>>? _sub;

  /// Set by the app shell to bring up the call screen.
  VoidCallback? presentCallScreen;

  CallPhase phase = CallPhase.idle;
  String? callId;
  String? conversationId;
  String? peerId;
  String peerName = '';
  bool video = false;
  bool outgoing = false;
  DateTime? answeredAt;
  String statusText = '';
  bool micMuted = false;
  bool speakerOn = false;
  bool cameraOff = false;
  bool remoteVideoOff = false;
  bool inPip = false;
  bool relayAvailable = true;
  int quality = 3;
  bool videoPausedForNetwork = false;

  final localRenderer = RTCVideoRenderer();
  final remoteRenderer = RTCVideoRenderer();
  bool _renderersReady = false;
  bool hasRemoteVideo = false;

  RTCPeerConnection? _pc;
  MediaStream? _local;
  RealtimeChannel? _signal;
  final _pendingIce = <RTCIceCandidate>[];
  bool _remoteSet = false;
  bool _gotOffer = false;
  int _restarts = 0;
  int _poorSamples = 0;
  int _goodSamples = 0;
  int _lastLost = 0;
  int _lastRecv = 0;
  Timer? _ringTimeout;
  Timer? _readyTimer;
  Timer? _statsTimer;
  Timer? _reconnectTimer;
  Timer? _tick;
  AudioPlayer? _tone;

  bool get inCall => phase != CallPhase.idle && phase != CallPhase.ended;
  Duration get elapsed => answeredAt == null ? Duration.zero : DateTime.now().difference(answeredAt!);

  // ------------------------------------------------------------ outgoing
  Future<void> startCall({required String conversationId, required String peerId, required String peerName, required bool video}) async {
    if (inCall) throw StateError('You are already in a call.');
    await _ensurePermissions(video);
    _reset();
    this.conversationId = conversationId;
    this.peerId = peerId;
    this.peerName = peerName;
    this.video = video;
    outgoing = true;
    speakerOn = video;
    phase = CallPhase.outgoing;
    statusText = 'Calling…';
    notifyListeners();
    presentCallScreen?.call();
    try {
      await _prepareMedia();
      final res = await sb.rpc('start_call', params: {'p_conversation_id': conversationId, 'p_media': video ? 'video' : 'audio'})
          as Map<String, dynamic>;
      callId = res['id'] as String;
      final status = res['status'] as String;
      if (status == 'busy') {
        _playTone('assets/sounds/busy.wav', loop: true);
        await _finish(text: '$peerName is on another call');
        return;
      }
      if (status == 'missed') {
        await _finish(text: '$peerName is not available');
        return;
      }
      await _joinSignal();
      statusText = 'Ringing…';
      notifyListeners();
      _playTone('assets/sounds/ringback.wav', loop: true);
      unawaited(sb.functions.invoke('push', body: {'type': 'call', 'call_id': callId}).then((_) {}, onError: (_) {}));
      _ringTimeout = Timer(const Duration(seconds: 45), () => hangUp(reason: 'no_answer'));
      unawaited(_startForegroundService());
    } catch (e) {
      debugPrint('start call failed: $e');
      await _finish(text: e is PostgrestException && e.message.contains('already_in_call') ? 'You are already in a call' : 'Call failed');
    }
  }

  // ------------------------------------------------------------ incoming
  void _onCallEvent(Map<String, dynamic> e) {
    final id = e['call_id'] as String?;
    final status = e['status'] as String?;
    if (id == null || status == null) return;
    if (status == 'ringing' && e['caller_id'] != core.userId) {
      if (inCall) return;
      _presentIncoming(e);
      return;
    }
    if (id != callId) return;
    switch (status) {
      case 'active':
        if (outgoing) {
          _ringTimeout?.cancel();
          _stopTone();
          phase = CallPhase.connecting;
          statusText = 'Connecting…';
          notifyListeners();
        }
      case 'declined':
        if (outgoing) _playTone('assets/sounds/busy.wav', loop: true);
        _finish(text: outgoing ? 'Call declined' : 'Call ended');
      case 'missed':
      case 'cancelled':
        if (!outgoing && phase == CallPhase.incoming) {
          NotificationService.instance.showMissedCall(caller: peerName, video: video);
        }
        _finish(text: 'Call ended');
      case 'ended':
      case 'failed':
      case 'busy':
        _finish(text: 'Call ended');
    }
  }

  void _presentIncoming(Map<String, dynamic> e) {
    _reset();
    callId = e['call_id'] as String;
    conversationId = e['conversation_id'] as String?;
    peerId = (e['caller_id'] ?? e['initiator_id']) as String?;
    peerName = (e['caller_name'] as String?) ?? core.profiles.nameOf(peerId);
    video = e['media'] == 'video';
    speakerOn = video;
    outgoing = false;
    phase = CallPhase.incoming;
    statusText = video ? 'Incoming video call' : 'Incoming voice call';
    notifyListeners();
    unawaited(native.invokeMethod('startRinging').then((_) {}, onError: (_) {}));
    unawaited(NotificationService.instance.showIncomingCall(callId: callId!, caller: peerName, video: video));
    _ringTimeout = Timer(const Duration(seconds: 60), () {
      if (phase == CallPhase.incoming) _finish(text: 'Missed call');
    });
    presentCallScreen?.call();
  }

  /// Picks up a ringing call after the app was opened from a notification.
  Future<void> checkIncoming() async {
    if (inCall) return;
    try {
      final res = await sb.rpc('get_incoming_call');
      if (res is Map<String, dynamic> && res['id'] != null) {
        _presentIncoming({
          'call_id': res['id'],
          'conversation_id': res['conversation_id'],
          'caller_id': res['initiator_id'],
          'media': res['media'],
        });
      }
    } catch (_) {}
  }

  Future<void> accept() async {
    if (phase != CallPhase.incoming || callId == null) return;
    _ringTimeout?.cancel();
    unawaited(native.invokeMethod('stopRinging').then((_) {}, onError: (_) {}));
    unawaited(NotificationService.instance.cancelCall(callId!));
    try {
      await _ensurePermissions(video);
      phase = CallPhase.connecting;
      statusText = 'Connecting…';
      notifyListeners();
      await _prepareMedia();
      await _joinSignal();
      await _createPeer();
      await sb.rpc('answer_call', params: {'p_call_id': callId});
      _sendReadyUntilOffer();
      unawaited(_startForegroundService());
    } catch (e) {
      debugPrint('accept failed: $e');
      await hangUp(reason: 'failed');
    }
  }

  Future<void> decline() async {
    final id = callId;
    if (id == null) return;
    unawaited(native.invokeMethod('stopRinging').then((_) {}, onError: (_) {}));
    unawaited(NotificationService.instance.cancelCall(id));
    try {
      await sb.rpc('end_call', params: {'p_call_id': id, 'p_reason': 'declined'});
    } catch (_) {}
    await _finish(text: 'Call declined');
  }

  Future<void> hangUp({String reason = 'hangup'}) async {
    final id = callId;
    _send({'type': 'hangup'});
    if (id != null) {
      try {
        await sb.rpc('end_call', params: {'p_call_id': id, 'p_reason': reason});
        if (reason == 'no_answer') {
          unawaited(sb.functions.invoke('push', body: {'type': 'missed_call', 'call_id': id}).then((_) {}, onError: (_) {}));
        }
      } catch (_) {}
    }
    await _finish(text: reason == 'no_answer' ? 'No answer' : (reason == 'failed' ? 'Connection lost' : 'Call ended'));
  }

  Future<void> endIfActive() async {
    if (inCall) await hangUp();
  }

  // ------------------------------------------------------------ signalling
  Future<void> _joinSignal() async {
    final ch = sb.channel('call:$callId', opts: const RealtimeChannelConfig(private: true));
    ch.onBroadcast(event: 'signal', callback: (p) {
      final inner = p['payload'];
      _onSignal(inner is Map ? Map<String, dynamic>.from(inner) : p);
    });
    final ready = Completer<void>();
    ch.subscribe((status, error) {
      if (status == RealtimeSubscribeStatus.subscribed && !ready.isCompleted) ready.complete();
      if ((status == RealtimeSubscribeStatus.channelError || status == RealtimeSubscribeStatus.timedOut) && !ready.isCompleted) {
        ready.completeError(error ?? 'signal_error');
      }
    });
    _signal = ch;
    await ready.future.timeout(const Duration(seconds: 15));
  }

  void _send(Map<String, dynamic> m) {
    final ch = _signal;
    if (ch == null) return;
    unawaited(ch.sendBroadcastMessage(event: 'signal', payload: {...m, 'from': core.userId}).then((_) {}, onError: (_) {}));
  }

  void _sendReadyUntilOffer() {
    var n = 0;
    _send({'type': 'ready', 'video': video});
    _readyTimer?.cancel();
    _readyTimer = Timer.periodic(const Duration(milliseconds: 1500), (t) {
      if (_gotOffer || n++ > 12 || !inCall) {
        t.cancel();
        return;
      }
      _send({'type': 'ready', 'video': video});
    });
  }

  Future<void> _onSignal(Map<String, dynamic> m) async {
    if (m['from'] == core.userId) return;
    try {
      switch (m['type']) {
        case 'ready':
          if (!outgoing) return;
          _ringTimeout?.cancel();
          _stopTone();
          if (phase == CallPhase.outgoing) {
            phase = CallPhase.connecting;
            statusText = 'Connecting…';
            notifyListeners();
          }
          if (_pc == null) await _createPeer();
          final existing = await _pc!.getLocalDescription();
          if (existing != null && existing.type == 'offer') {
            _send({'type': 'offer', 'sdp': existing.sdp});
          } else {
            await _makeOffer();
          }
        case 'offer':
          _gotOffer = true;
          _readyTimer?.cancel();
          if (_pc == null) await _createPeer();
          await _pc!.setRemoteDescription(RTCSessionDescription(m['sdp'] as String, 'offer'));
          _remoteSet = true;
          await _flushIce();
          final answer = await _pc!.createAnswer({});
          await _pc!.setLocalDescription(answer);
          _send({'type': 'answer', 'sdp': answer.sdp});
        case 'answer':
          if (_pc == null) return;
          await _pc!.setRemoteDescription(RTCSessionDescription(m['sdp'] as String, 'answer'));
          _remoteSet = true;
          await _flushIce();
        case 'ice':
          final c = RTCIceCandidate(m['candidate'] as String?, m['sdpMid'] as String?, (m['sdpMLineIndex'] as num?)?.toInt());
          if (_pc != null && _remoteSet) {
            await _pc!.addCandidate(c);
          } else {
            _pendingIce.add(c);
          }
        case 'video':
          remoteVideoOff = m['off'] == true;
          notifyListeners();
        case 'hangup':
          await _finish(text: 'Call ended');
      }
    } catch (e) {
      debugPrint('signal ${m['type']} failed: $e');
    }
  }

  Future<void> _flushIce() async {
    final list = List.of(_pendingIce);
    _pendingIce.clear();
    for (final c in list) {
      try {
        await _pc!.addCandidate(c);
      } catch (_) {}
    }
  }

  Future<void> _makeOffer({bool restart = false}) async {
    final offer = await _pc!.createOffer(restart ? {'iceRestart': true} : {});
    await _pc!.setLocalDescription(offer);
    _send({'type': 'offer', 'sdp': offer.sdp, 'restart': restart});
  }

  // ------------------------------------------------------------ media
  Future<void> _ensurePermissions(bool withVideo) async {
    final mic = await Permission.microphone.request();
    if (!mic.isGranted) throw StateError('Microphone permission is needed for calls.');
    if (withVideo) {
      final cam = await Permission.camera.request();
      if (!cam.isGranted) throw StateError('Camera permission is needed for video calls.');
    }
    if (await Permission.bluetoothConnect.isDenied) {
      await Permission.bluetoothConnect.request();
    }
  }

  Future<void> _prepareMedia() async {
    if (!_renderersReady) {
      await localRenderer.initialize();
      await remoteRenderer.initialize();
      _renderersReady = true;
    }
    try {
      await Helper.setAndroidAudioConfiguration(AndroidAudioConfiguration.communication);
    } catch (_) {}
    _local = await navigator.mediaDevices.getUserMedia({
      'audio': {'echoCancellation': true, 'noiseSuppression': true, 'autoGainControl': true},
      'video': video
          ? {
              'facingMode': 'user',
              'width': {'ideal': 640},
              'height': {'ideal': 480},
              'frameRate': {'ideal': 24, 'max': 30},
            }
          : false,
    });
    if (video) localRenderer.srcObject = _local;
    await Helper.setSpeakerphoneOn(speakerOn);
    await WakelockPlus.enable();
    if (!video) unawaited(native.invokeMethod('setProximity', {'enabled': true}).then((_) {}, onError: (_) {}));
    unawaited(native.invokeMethod('setPipAllowed', {'allowed': video}).then((_) {}, onError: (_) {}));
  }

  Future<List<Map<String, dynamic>>> _iceServers() async {
    try {
      final res = await sb.functions.invoke('ice-servers').timeout(const Duration(seconds: 6));
      final data = res.data;
      if (data is Map && data['iceServers'] is List) {
        relayAvailable = data['relay'] == true;
        return (data['iceServers'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
      }
    } catch (e) {
      debugPrint('ice servers: $e');
    }
    relayAvailable = false;
    return [
      {'urls': ['stun:stun.l.google.com:19302', 'stun:stun1.l.google.com:19302']},
    ];
  }

  Future<void> _createPeer() async {
    final servers = await _iceServers();
    final pc = await createPeerConnection({
      'iceServers': servers,
      'sdpSemantics': 'unified-plan',
      'bundlePolicy': 'max-bundle',
      'iceCandidatePoolSize': 2,
    });
    _pc = pc;
    for (final t in _local?.getTracks() ?? <MediaStreamTrack>[]) {
      await pc.addTrack(t, _local!);
    }
    pc.onIceCandidate = (c) {
      if (c.candidate != null) {
        _send({'type': 'ice', 'candidate': c.candidate, 'sdpMid': c.sdpMid, 'sdpMLineIndex': c.sdpMLineIndex});
      }
    };
    pc.onTrack = (e) {
      if (e.track.kind == 'video' && e.streams.isNotEmpty) {
        remoteRenderer.srcObject = e.streams.first;
        hasRemoteVideo = true;
        notifyListeners();
      }
    };
    pc.onIceConnectionState = _onIceState;
  }

  void _onIceState(RTCIceConnectionState s) {
    switch (s) {
      case RTCIceConnectionState.RTCIceConnectionStateConnected:
      case RTCIceConnectionState.RTCIceConnectionStateCompleted:
        _reconnectTimer?.cancel();
        _restarts = 0;
        answeredAt ??= DateTime.now();
        phase = CallPhase.active;
        statusText = '';
        _tick ??= Timer.periodic(const Duration(seconds: 1), (_) => notifyListeners());
        _statsTimer ??= Timer.periodic(const Duration(seconds: 3), (_) => _sampleStats());
        unawaited(_applyVideoQuality());
        notifyListeners();
      case RTCIceConnectionState.RTCIceConnectionStateDisconnected:
        if (phase == CallPhase.active) {
          phase = CallPhase.reconnecting;
          statusText = 'Reconnecting…';
          notifyListeners();
        }
        _reconnectTimer?.cancel();
        _reconnectTimer = Timer(const Duration(seconds: 4), _tryRestart);
      case RTCIceConnectionState.RTCIceConnectionStateFailed:
        phase = CallPhase.reconnecting;
        statusText = 'Reconnecting…';
        notifyListeners();
        _tryRestart();
      default:
        break;
    }
  }

  Future<void> _tryRestart() async {
    if (!inCall || _pc == null) return;
    if (_restarts >= 4) {
      await hangUp(reason: 'failed');
      return;
    }
    _restarts++;
    if (outgoing) {
      try {
        await _makeOffer(restart: true);
      } catch (_) {}
    }
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 8), () {
      if (phase == CallPhase.reconnecting) _tryRestart();
    });
  }

  Future<void> _sampleStats() async {
    final pc = _pc;
    if (pc == null) return;
    try {
      final reports = await pc.getStats();
      double? rtt;
      var lost = 0;
      var received = 0;
      for (final r in reports) {
        final v = r.values;
        if (r.type == 'candidate-pair' && v['state'] == 'succeeded' && v['currentRoundTripTime'] != null) {
          rtt = (v['currentRoundTripTime'] as num).toDouble();
        }
        if (r.type == 'inbound-rtp' && v['kind'] == 'audio') {
          lost += (v['packetsLost'] as num?)?.toInt() ?? 0;
          received += (v['packetsReceived'] as num?)?.toInt() ?? 0;
        }
      }
      final dLost = (lost - _lastLost).clamp(0, 1 << 30);
      final dRecv = (received - _lastRecv).clamp(0, 1 << 30);
      _lastLost = lost;
      _lastRecv = received;
      final loss = dLost + dRecv == 0 ? 0.0 : dLost / (dLost + dRecv);
      final r = rtt ?? 0;
      final q = (loss > 0.12 || r > 0.7) ? 1 : ((loss > 0.04 || r > 0.35) ? 2 : 3);
      if (q == 1) {
        _poorSamples++;
        _goodSamples = 0;
      } else {
        _goodSamples++;
        _poorSamples = 0;
      }
      final pause = video && _poorSamples >= 2 && loss > 0.2;
      final resume = videoPausedForNetwork && _goodSamples >= 3;
      final changed = q != quality || pause != videoPausedForNetwork || resume;
      quality = q;
      if (pause) videoPausedForNetwork = true;
      if (resume) videoPausedForNetwork = false;
      if (changed) {
        await _applyVideoQuality();
        notifyListeners();
      }
    } catch (_) {}
  }

  /// Adaptive bitrate: protects audio by shrinking or pausing video on poor networks.
  Future<void> _applyVideoQuality() async {
    final pc = _pc;
    if (pc == null || !video) return;
    try {
      for (final s in await pc.getSenders()) {
        if (s.track?.kind != 'video') continue;
        final params = s.parameters;
        final encodings = params.encodings;
        if (encodings == null || encodings.isEmpty) continue;
        final e = encodings.first;
        e.active = !videoPausedForNetwork && !cameraOff;
        switch (quality) {
          case 1:
            e.maxBitrate = 160000;
            e.maxFramerate = 12;
            e.scaleResolutionDownBy = 2.0;
          case 2:
            e.maxBitrate = 450000;
            e.maxFramerate = 20;
            e.scaleResolutionDownBy = 1.5;
          default:
            e.maxBitrate = 1000000;
            e.maxFramerate = 24;
            e.scaleResolutionDownBy = 1.0;
        }
        await s.setParameters(params);
      }
    } catch (e) {
      debugPrint('bitrate: $e');
    }
  }

  // ------------------------------------------------------------ controls
  void toggleMute() {
    micMuted = !micMuted;
    for (final t in _local?.getAudioTracks() ?? <MediaStreamTrack>[]) {
      t.enabled = !micMuted;
    }
    notifyListeners();
  }

  Future<void> toggleSpeaker() async {
    speakerOn = !speakerOn;
    await Helper.setSpeakerphoneOn(speakerOn);
    notifyListeners();
  }

  Future<List<MediaDeviceInfo>> audioOutputs() async {
    try {
      return await Helper.audiooutputs;
    } catch (_) {
      return [];
    }
  }

  Future<void> selectOutput(MediaDeviceInfo d) async {
    await Helper.selectAudioOutput(d.deviceId);
    speakerOn = d.deviceId.toLowerCase().contains('speaker');
    notifyListeners();
  }

  void toggleCamera() {
    cameraOff = !cameraOff;
    for (final t in _local?.getVideoTracks() ?? <MediaStreamTrack>[]) {
      t.enabled = !cameraOff;
    }
    _send({'type': 'video', 'off': cameraOff});
    notifyListeners();
  }

  Future<void> switchCamera() async {
    final tracks = _local?.getVideoTracks() ?? [];
    if (tracks.isNotEmpty) await Helper.switchCamera(tracks.first);
  }

  Future<void> enterPip() async {
    try {
      await native.invokeMethod('enterPip');
    } catch (_) {}
  }

  // ------------------------------------------------------------ teardown
  void _playTone(String asset, {bool loop = false}) {
    _stopTone();
    final p = AudioPlayer();
    _tone = p;
    p.setAsset(asset).then((_) async {
      await p.setLoopMode(loop ? LoopMode.one : LoopMode.off);
      await p.play();
    }).catchError((_) {});
  }

  void _stopTone() {
    final t = _tone;
    _tone = null;
    if (t != null) {
      t.stop().then((_) => t.dispose()).catchError((_) {});
    }
  }

  Future<void> _startForegroundService() async {
    try {
      await native.invokeMethod('startCallService', {'video': video, 'title': peerName});
    } catch (_) {}
  }

  Future<void> _finish({String? text}) async {
    if (phase == CallPhase.idle || phase == CallPhase.ended) return;
    phase = CallPhase.ended;
    statusText = text ?? 'Call ended';
    for (final t in [_ringTimeout, _readyTimer, _statsTimer, _reconnectTimer, _tick]) {
      t?.cancel();
    }
    _ringTimeout = _readyTimer = _statsTimer = _reconnectTimer = _tick = null;
    final id = callId;
    if (id != null) unawaited(NotificationService.instance.cancelCall(id));
    unawaited(native.invokeMethod('stopRinging').then((_) {}, onError: (_) {}));
    unawaited(native.invokeMethod('stopCallService').then((_) {}, onError: (_) {}));
    unawaited(native.invokeMethod('setProximity', {'enabled': false}).then((_) {}, onError: (_) {}));
    unawaited(native.invokeMethod('setPipAllowed', {'allowed': false}).then((_) {}, onError: (_) {}));
    notifyListeners();
    await _teardown();
    Future.delayed(const Duration(milliseconds: 1800), () {
      if (phase == CallPhase.ended) {
        _stopTone();
        phase = CallPhase.idle;
        notifyListeners();
      }
    });
  }

  Future<void> _teardown() async {
    try {
      await WakelockPlus.disable();
    } catch (_) {}
    final ch = _signal;
    _signal = null;
    if (ch != null) unawaited(sb.removeChannel(ch));
    try {
      for (final t in _local?.getTracks() ?? <MediaStreamTrack>[]) {
        await t.stop();
      }
      await _local?.dispose();
    } catch (_) {}
    _local = null;
    try {
      await _pc?.close();
      await _pc?.dispose();
    } catch (_) {}
    _pc = null;
    if (_renderersReady) {
      localRenderer.srcObject = null;
      remoteRenderer.srcObject = null;
    }
    try {
      await Helper.clearAndroidCommunicationDevice();
    } catch (_) {}
  }

  void _reset() {
    callId = null;
    conversationId = null;
    peerId = null;
    peerName = '';
    answeredAt = null;
    micMuted = false;
    cameraOff = false;
    remoteVideoOff = false;
    hasRemoteVideo = false;
    quality = 3;
    videoPausedForNetwork = false;
    _pendingIce.clear();
    _remoteSet = false;
    _gotOffer = false;
    _restarts = 0;
    _poorSamples = 0;
    _goodSamples = 0;
    _lastLost = 0;
    _lastRecv = 0;
  }

  @override
  void dispose() {
    _sub?.cancel();
    _stopTone();
    if (_renderersReady) {
      localRenderer.dispose();
      remoteRenderer.dispose();
    }
    super.dispose();
  }
}
