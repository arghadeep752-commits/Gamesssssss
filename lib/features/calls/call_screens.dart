import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import '../../services/session.dart';
import '../contacts/contacts.dart';
import 'call_controller.dart';

/// Full-screen call UI. The call itself lives in [CallController] and keeps
/// running when this screen is minimised.
class CallScreen extends ConsumerStatefulWidget {
  const CallScreen({super.key});

  /// True while the screen is on the navigation stack.
  static bool isOpen = false;

  @override
  ConsumerState<CallScreen> createState() => _CallScreenState();
}

class _CallScreenState extends ConsumerState<CallScreen> with SingleTickerProviderStateMixin {
  late final HimeCore core = ref.read(coreProvider);
  CallController get c => core.calls;
  late final AnimationController _pulse = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))..repeat();
  Timer? _ticker;
  Offset _pip = const Offset(16, 96);
  bool _closing = false;

  @override
  void initState() {
    super.initState();
    CallScreen.isOpen = true;
    c.addListener(_onCall);
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted && c.phase == CallPhase.active) setState(() {});
    });
    // Opened without a call (e.g. a stale notification): leave right away.
    WidgetsBinding.instance.addPostFrameCallback((_) => _onCall());
  }

  void _onCall() {
    if (!mounted) return;
    if (c.phase == CallPhase.idle && !_closing) {
      _closing = true;
      if (context.canPop()) {
        context.pop();
      } else {
        context.go('/chats');
      }
      return;
    }
    setState(() {});
  }

  @override
  void dispose() {
    CallScreen.isOpen = false;
    c.removeListener(_onCall);
    _ticker?.cancel();
    _pulse.dispose();
    super.dispose();
  }

  void _minimise() {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/chats');
    }
  }

  Future<void> _pickOutput() async {
    final outs = await c.audioOutputs();
    if (!mounted) return;
    if (outs.length <= 1) {
      await c.toggleSpeaker();
      return;
    }
    await showActionSheet(context, title: 'Audio output', actions: [
      for (final o in outs)
        SheetAction(
          o.label.toLowerCase().contains('bluetooth')
              ? Icons.bluetooth_audio_rounded
              : o.label.toLowerCase().contains('speaker')
                  ? Icons.volume_up_rounded
                  : Icons.phone_in_talk_rounded,
          o.label.isEmpty ? o.deviceId : o.label,
          () => c.selectOutput(o),
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final showRemoteVideo = c.video && c.hasRemoteVideo && !c.remoteVideoOff;
    final showLocalVideo = c.video && !c.cameraOff && c.phase != CallPhase.ended;
    if (c.inPip) {
      return Scaffold(
        backgroundColor: Colors.black,
        body: showRemoteVideo
            ? RTCVideoView(c.remoteRenderer, objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover)
            : Center(child: HimeAvatar(name: c.peerName, path: core.profiles.cached(c.peerId)?.avatarPath, size: 72)),
      );
    }
    final peer = core.profiles.cached(c.peerId);
    return PopScope(
      canPop: c.phase != CallPhase.incoming,
      child: Scaffold(
        backgroundColor: HimeColors.ink,
        body: Stack(children: [
          Positioned.fill(
            child: showRemoteVideo
                ? RTCVideoView(c.remoteRenderer, objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover)
                : DecoratedBox(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [Color(0xFF2A2B2F), HimeColors.ink, Color(0xFF15161A)],
                      ),
                    ),
                    child: c.video && !c.hasRemoteVideo && showLocalVideo && c.phase != CallPhase.active
                        ? RTCVideoView(c.localRenderer, mirror: true, objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover)
                        : null,
                  ),
          ),
          if (showRemoteVideo)
            Positioned.fill(
              child: IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [Colors.black.withValues(alpha: 0.45), Colors.transparent, Colors.transparent, Colors.black.withValues(alpha: 0.55)],
                    ),
                  ),
                ),
              ),
            ),
          SafeArea(
            child: Column(children: [
              Row(children: [
                IconButton(
                  tooltip: 'Minimise',
                  color: Colors.white,
                  icon: const Icon(Icons.keyboard_arrow_down_rounded, size: 30),
                  onPressed: c.phase == CallPhase.incoming ? null : _minimise,
                ),
                const Spacer(),
                const Icon(Icons.lock_rounded, color: Colors.white70, size: 14),
                const SizedBox(width: 6),
                const Text('End-to-end encrypted', style: TextStyle(color: Colors.white70, fontSize: 12.5)),
                const Spacer(),
                if (c.video && c.phase == CallPhase.active)
                  IconButton(tooltip: 'Picture in picture', color: Colors.white, icon: const Icon(Icons.picture_in_picture_alt_rounded), onPressed: c.enterPip)
                else
                  const SizedBox(width: 48),
              ]),
              if (!showRemoteVideo) ...[
                const SizedBox(height: 36),
                SizedBox(
                  width: 180,
                  height: 180,
                  child: Stack(alignment: Alignment.center, children: [
                    if (c.phase == CallPhase.outgoing || c.phase == CallPhase.incoming)
                      AnimatedBuilder(
                        animation: _pulse,
                        builder: (_, __) => Container(
                          width: 120 + 60 * _pulse.value,
                          height: 120 + 60 * _pulse.value,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: HimeColors.yellow.withValues(alpha: 0.28 * (1 - _pulse.value)),
                          ),
                        ),
                      ),
                    HimeAvatar(name: c.peerName, path: peer?.avatarPath, version: peer?.avatarVersion ?? 0, size: 120),
                  ]),
                ),
                const SizedBox(height: 16),
              ] else
                const SizedBox(height: 12),
              Text(c.peerName,
                  style: const TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.w700, fontFamily: 'Poppins'),
                  textAlign: TextAlign.center),
              const SizedBox(height: 6),
              Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                if (c.phase == CallPhase.active) ...[
                  _QualityBars(quality: c.quality),
                  const SizedBox(width: 8),
                ],
                Text(
                  c.phase == CallPhase.active ? Fmt.duration(c.elapsed) : c.statusText,
                  style: const TextStyle(color: Colors.white70, fontSize: 15),
                ),
              ]),
              if (c.remoteVideoOff && c.video && c.phase == CallPhase.active)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text('Camera is off', style: TextStyle(color: Colors.white60)),
                ),
              if (c.videoPausedForNetwork)
                Container(
                  margin: const EdgeInsets.only(top: 12),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(20)),
                  child: const Text('Poor connection — video paused', style: TextStyle(color: Colors.white)),
                ),
              if (c.phase == CallPhase.reconnecting)
                const Padding(
                  padding: EdgeInsets.only(top: 12),
                  child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: HimeColors.yellow)),
                ),
              const Spacer(),
              _controls(),
              const SizedBox(height: 28),
            ]),
          ),
          if (showLocalVideo && (showRemoteVideo || c.phase == CallPhase.active))
            Positioned(
              left: _pip.dx,
              top: _pip.dy,
              child: GestureDetector(
                onPanUpdate: (d) {
                  final size = MediaQuery.of(context).size;
                  setState(() {
                    _pip = Offset(
                      (_pip.dx + d.delta.dx).clamp(8.0, size.width - 128.0),
                      (_pip.dy + d.delta.dy).clamp(48.0, size.height - 220.0),
                    );
                  });
                },
                onTap: c.switchCamera,
                child: Container(
                  width: 112,
                  height: 160,
                  clipBehavior: Clip.antiAlias,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white24, width: 1.5),
                    color: Colors.black,
                  ),
                  child: RTCVideoView(c.localRenderer, mirror: true, objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover),
                ),
              ),
            ),
        ]),
      ),
    );
  }

  Widget _controls() {
    if (c.phase == CallPhase.incoming) {
      return Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
        _RoundButton(icon: Icons.call_end_rounded, label: 'Decline', color: HimeColors.danger, onTap: c.decline, size: 72),
        _RoundButton(
          icon: c.video ? Icons.videocam_rounded : Icons.call_rounded,
          label: 'Accept',
          color: HimeColors.online,
          onTap: c.accept,
          size: 72,
        ),
      ]);
    }
    final ended = c.phase == CallPhase.ended;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(32)),
      child: Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
        _RoundButton(
          icon: c.speakerOn ? Icons.volume_up_rounded : Icons.hearing_rounded,
          label: 'Audio',
          active: c.speakerOn,
          onTap: ended ? null : _pickOutput,
        ),
        if (c.video)
          _RoundButton(
            icon: c.cameraOff ? Icons.videocam_off_rounded : Icons.videocam_rounded,
            label: 'Camera',
            active: !c.cameraOff,
            onTap: ended ? null : c.toggleCamera,
          ),
        if (c.video)
          _RoundButton(icon: Icons.cameraswitch_rounded, label: 'Flip', onTap: ended || c.cameraOff ? null : c.switchCamera),
        _RoundButton(
          icon: c.micMuted ? Icons.mic_off_rounded : Icons.mic_rounded,
          label: c.micMuted ? 'Unmute' : 'Mute',
          active: c.micMuted,
          onTap: ended ? null : c.toggleMute,
        ),
        _RoundButton(icon: Icons.call_end_rounded, label: 'End', color: HimeColors.danger, onTap: ended ? null : () => c.hangUp()),
      ]),
    );
  }
}

class _RoundButton extends StatelessWidget {
  const _RoundButton({required this.icon, required this.label, this.onTap, this.color, this.active = false, this.size = 56});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final Color? color;
  final bool active;
  final double size;

  @override
  Widget build(BuildContext context) {
    final bg = color ?? (active ? Colors.white : Colors.white.withValues(alpha: 0.16));
    final fg = color != null ? Colors.white : (active ? HimeColors.ink : Colors.white);
    return Opacity(
      opacity: onTap == null ? 0.45 : 1,
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Pressable(
          onTap: onTap,
          scale: 0.9,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            width: size,
            height: size,
            decoration: BoxDecoration(color: bg, shape: BoxShape.circle),
            child: Icon(icon, color: fg, size: size * 0.45),
          ),
        ),
        const SizedBox(height: 6),
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)),
      ]),
    );
  }
}

class _QualityBars extends StatelessWidget {
  const _QualityBars({required this.quality});
  final int quality;

  @override
  Widget build(BuildContext context) {
    final color = quality >= 3 ? HimeColors.online : (quality == 2 ? HimeColors.yellow : HimeColors.danger);
    return Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
      for (var i = 1; i <= 3; i++)
        Container(
          width: 4,
          height: 5.0 + i * 4,
          margin: const EdgeInsets.only(right: 2),
          decoration: BoxDecoration(color: i <= quality ? color : Colors.white24, borderRadius: BorderRadius.circular(2)),
        ),
    ]);
  }
}

// ---------------------------------------------------------------- history

class CallsScreen extends ConsumerStatefulWidget {
  const CallsScreen({super.key});

  @override
  ConsumerState<CallsScreen> createState() => _CallsScreenState();
}

class _CallsScreenState extends ConsumerState<CallsScreen> {
  late final HimeCore core = ref.read(coreProvider);
  List<Map<String, dynamic>>? calls;
  Object? error;
  StreamSubscription<Map<String, dynamic>>? _sub;

  @override
  void initState() {
    super.initState();
    _load();
    _sub = core.realtime.calls.listen((_) => _load());
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final rows = (await core.sb.rpc('get_call_history', params: {'p_limit': 100, 'p_before': null}) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      if (mounted) {
        setState(() {
          calls = rows;
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  Future<void> _call(String conversationId, String peerId, String name, bool video) async {
    try {
      await core.calls.startCall(conversationId: conversationId, peerId: peerId, peerName: name, video: video);
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
  }

  Future<void> _newCall() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SizedBox(
        height: MediaQuery.of(ctx).size.height * 0.85,
        child: Column(children: [
          Padding(padding: const EdgeInsets.all(8), child: Text('New call', style: ctx.text.titleMedium)),
          Expanded(
            child: PeoplePicker(
              core: core,
              onPick: (p) async {
                Navigator.pop(ctx);
                final video = await showModalBottomSheet<bool>(
                  context: context,
                  builder: (c2) => SafeArea(
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      ListTile(leading: const Icon(Icons.call_rounded), title: Text('Voice call ${p.name}'), onTap: () => Navigator.pop(c2, false)),
                      ListTile(leading: const Icon(Icons.videocam_rounded), title: Text('Video call ${p.name}'), onTap: () => Navigator.pop(c2, true)),
                    ]),
                  ),
                );
                if (video == null) return;
                try {
                  final conv = await core.sb.rpc('get_or_create_direct', params: {'p_other': p.id}) as String;
                  await _call(conv, p.id, p.name, video);
                } catch (e) {
                  if (mounted) toast(context, friendlyError(e));
                }
              },
            ),
          ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final list = calls;
    return Scaffold(
      appBar: AppBar(title: const Text('Calls')),
      floatingActionButton: FloatingActionButton(onPressed: _newCall, tooltip: 'New call', child: const Icon(Icons.add_call)),
      body: error != null && list == null
          ? ErrorState(error: error!, onRetry: _load)
          : list == null
              ? const ListSkeleton()
              : RefreshIndicator(
                  onRefresh: _load,
                  child: list.isEmpty
                      ? ListView(children: const [
                          SizedBox(height: 60),
                          EmptyState(
                            icon: Icons.call_outlined,
                            title: 'No calls yet',
                            message: 'Voice and video calls on Hime are end-to-end encrypted. Tap + to start one.',
                          ),
                        ])
                      : ListView.builder(
                          padding: const EdgeInsets.only(bottom: 96),
                          itemCount: list.length,
                          itemBuilder: (context, i) {
                            final r = list[i];
                            final outgoing = r['outgoing'] == true;
                            final status = r['status'] as String? ?? '';
                            final missed = !outgoing && (status == 'missed' || status == 'cancelled');
                            final video = r['media'] == 'video';
                            final at = parseTime(r['created_at']) ?? DateTime.now();
                            final secs = (r['duration_seconds'] as num?)?.toInt() ?? 0;
                            final name = (r['peer_name'] as String?) ?? 'Hime user';
                            final peerId = r['peer_id'] as String?;
                            return ListTile(
                              leading: HimeAvatar(
                                name: name,
                                path: r['peer_avatar_path'] as String?,
                                version: (r['peer_avatar_version'] as num?)?.toInt() ?? 0,
                                size: 46,
                              ),
                              title: Text(name, style: TextStyle(color: missed ? HimeColors.danger : null, fontWeight: FontWeight.w600)),
                              subtitle: Row(children: [
                                Icon(
                                  outgoing ? Icons.call_made_rounded : (missed ? Icons.call_missed_rounded : Icons.call_received_rounded),
                                  size: 16,
                                  color: missed ? HimeColors.danger : (outgoing ? HimeColors.online : context.palette.muted),
                                ),
                                const SizedBox(width: 4),
                                Flexible(
                                  child: Text(
                                    '${Fmt.chatTime(at)}${status == 'ended' && secs > 0 ? ' · ${Fmt.duration(Duration(seconds: secs))}' : ''}${status == 'declined' ? ' · Declined' : ''}',
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ]),
                              trailing: IconButton(
                                tooltip: video ? 'Video call' : 'Voice call',
                                icon: Icon(video ? Icons.videocam_outlined : Icons.call_outlined, color: HimeColors.yellowDeep),
                                onPressed: peerId == null ? null : () => _call(r['conversation_id'] as String, peerId, name, video),
                              ),
                              onTap: () => context.push('/chat/${r['conversation_id']}'),
                            );
                          },
                        ),
                ),
    );
  }
}
