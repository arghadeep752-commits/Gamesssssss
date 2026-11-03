import 'dart:async';
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show FileOptions;
import 'package:uuid/uuid.dart';
import 'package:video_player/video_player.dart';

import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import '../../services/session.dart';
import '../chats/message_widgets.dart';
import '../chats/models.dart';
import '../contacts/contacts.dart';

// ---------------------------------------------------------------- models

class StatusItem {
  StatusItem({
    required this.id,
    required this.kind,
    this.body,
    this.background = '#202124',
    this.font = 0,
    this.mediaPath,
    this.caption,
    this.durationMs,
    required this.createdAt,
    this.viewed = false,
  });

  final String id;
  final String kind;
  final String? body;
  final String background;
  final int font;
  final String? mediaPath;
  final String? caption;
  final int? durationMs;
  final DateTime createdAt;
  bool viewed;

  factory StatusItem.fromJson(Map<String, dynamic> j) => StatusItem(
        id: j['id'] as String,
        kind: j['kind'] as String,
        body: j['body'] as String?,
        background: (j['background'] as String?) ?? '#202124',
        font: (j['font'] as num?)?.toInt() ?? 0,
        mediaPath: j['media_path'] as String?,
        caption: j['caption'] as String?,
        durationMs: (j['duration_ms'] as num?)?.toInt(),
        createdAt: parseTime(j['created_at']) ?? DateTime.now(),
        viewed: j['viewed'] == true,
      );
}

class StatusUser {
  StatusUser({
    required this.userId,
    required this.name,
    this.avatarPath,
    this.avatarVersion = 0,
    this.muted = false,
    required this.items,
    this.mine = false,
  });

  final String userId;
  final String name;
  final String? avatarPath;
  final int avatarVersion;
  final bool muted;
  final List<StatusItem> items;
  final bool mine;

  bool get allViewed => items.every((i) => i.viewed);
  DateTime get latest => items.isEmpty ? DateTime.fromMillisecondsSinceEpoch(0) : items.last.createdAt;
}

class StatusViewerArgs {
  const StatusViewerArgs(this.users, this.index);
  final List<StatusUser> users;
  final int index;
}

Color hexColor(String hex) {
  final v = int.tryParse(hex.replaceFirst('#', ''), radix: 16) ?? 0x202124;
  return Color(0xFF000000 | v);
}

String colorHex(Color c) =>
    '#${(c.toARGB32() & 0xFFFFFF).toRadixString(16).padLeft(6, '0').toUpperCase()}';

TextStyle statusFont(int font) {
  switch (font) {
    case 1:
      return const TextStyle(fontFamily: 'serif', fontWeight: FontWeight.w600);
    case 2:
      return const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w600);
    case 3:
      return const TextStyle(fontFamily: 'Poppins', fontWeight: FontWeight.w500, fontStyle: FontStyle.italic);
    case 4:
      return const TextStyle(fontFamily: 'sans-serif-condensed', fontWeight: FontWeight.w700);
    default:
      return const TextStyle(fontFamily: 'Poppins', fontWeight: FontWeight.w700);
  }
}

// ---------------------------------------------------------------- repo

class StatusRepo {
  StatusRepo(this.core);
  final HimeCore core;
  static const _uuid = Uuid();

  Future<List<StatusUser>> feed() async {
    final rows = (await core.sb.rpc('get_status_feed') as List<dynamic>).cast<Map<String, dynamic>>();
    return [
      for (final r in rows)
        StatusUser(
          userId: r['user_id'] as String,
          name: (r['display_name'] as String?) ?? 'Hime user',
          avatarPath: r['avatar_path'] as String?,
          avatarVersion: (r['avatar_version'] as num?)?.toInt() ?? 0,
          muted: r['muted'] == true,
          items: ((r['statuses'] as List?) ?? const []).map((e) => StatusItem.fromJson(Map<String, dynamic>.from(e as Map))).toList(),
        ),
    ];
  }

  Future<List<StatusItem>> mine() async {
    final rows = await core.sb
        .from('statuses')
        .select()
        .eq('user_id', core.userId)
        .gt('expires_at', DateTime.now().toUtc().toIso8601String())
        .order('created_at');
    return rows.map((r) => StatusItem.fromJson({...r, 'viewed': true})).toList();
  }

  Future<void> postText(String body, String background, int font) =>
      core.sb.from('statuses').insert({'user_id': core.userId, 'kind': 'text', 'body': body, 'background': background, 'font': font});

  Future<void> postMedia(XFile file, {required bool video, String? caption, int? durationMs}) async {
    final ext = video ? 'mp4' : 'jpg';
    final path = '${core.userId}/${_uuid.v4()}.$ext';
    final bytes = await file.readAsBytes();
    if (bytes.length > 16 * 1024 * 1024) throw StateError('Status files can be up to 16 MB.');
    await core.sb.storage.from('status').uploadBinary(path, bytes,
        fileOptions: FileOptions(contentType: video ? 'video/mp4' : 'image/jpeg', upsert: false));
    await core.sb.from('statuses').insert({
      'user_id': core.userId,
      'kind': video ? 'video' : 'image',
      'media_path': path,
      if (caption != null && caption.isNotEmpty) 'caption': caption,
      'duration_ms': ?durationMs,
    });
  }

  Future<void> delete(StatusItem s) async {
    await core.sb.from('statuses').delete().eq('id', s.id);
    if (s.mediaPath != null) {
      try {
        await core.sb.storage.from('status').remove([s.mediaPath!]);
      } catch (_) {}
    }
  }

  Future<void> setMuted(String userId, bool muted) async {
    if (muted) {
      await core.sb.from('status_mutes').upsert({'user_id': core.userId, 'muted_user_id': userId},
          onConflict: 'user_id,muted_user_id', ignoreDuplicates: true);
    } else {
      await core.sb.from('status_mutes').delete().eq('user_id', core.userId).eq('muted_user_id', userId);
    }
  }
}

// ---------------------------------------------------------------- updates tab

class UpdatesScreen extends ConsumerStatefulWidget {
  const UpdatesScreen({super.key});

  @override
  ConsumerState<UpdatesScreen> createState() => _UpdatesScreenState();
}

class _UpdatesScreenState extends ConsumerState<UpdatesScreen> {
  late final HimeCore core = ref.read(coreProvider);
  late final repo = StatusRepo(core);
  List<StatusUser>? feed;
  List<StatusItem> mine = [];
  Object? error;
  bool posting = false;
  bool showMuted = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final f = await repo.feed();
      final m = await repo.mine();
      if (mounted) {
        setState(() {
          feed = f;
          mine = m;
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  Future<void> _addMedia() async {
    final choice = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.photo_camera_rounded), title: const Text('Take photo'), onTap: () => Navigator.pop(ctx, 'camera')),
          ListTile(leading: const Icon(Icons.photo_library_rounded), title: const Text('Photo from gallery'), onTap: () => Navigator.pop(ctx, 'gallery')),
          ListTile(leading: const Icon(Icons.videocam_rounded), title: const Text('Video (up to 30 s)'), onTap: () => Navigator.pop(ctx, 'video')),
        ]),
      ),
    );
    if (choice == null) return;
    final picker = ImagePicker();
    XFile? file;
    if (choice == 'video') {
      file = await picker.pickVideo(source: ImageSource.gallery, maxDuration: const Duration(seconds: 30));
    } else {
      file = await picker.pickImage(
          source: choice == 'camera' ? ImageSource.camera : ImageSource.gallery, maxWidth: 1440, maxHeight: 1440, imageQuality: 82);
    }
    if (file == null || !mounted) return;
    final caption = await promptText(context, title: 'Add a caption', hint: 'Optional', maxLength: 700, maxLines: 3);
    if (caption == null || !mounted) return;
    setState(() => posting = true);
    int? duration;
    if (choice == 'video') {
      final vc = VideoPlayerController.file(File(file.path));
      try {
        await vc.initialize();
        duration = math.min(vc.value.duration.inMilliseconds, 30000);
      } catch (_) {
        duration = 30000;
      } finally {
        await vc.dispose();
      }
    }
    final ok = await guard(context, () => repo.postMedia(file!, video: choice == 'video', caption: caption, durationMs: duration),
        success: 'Status posted');
    if (mounted) setState(() => posting = false);
    if (ok) await _load();
  }

  void _openMine() {
    if (mine.isEmpty) {
      _addMedia();
      return;
    }
    final me = ref.read(sessionProvider).profile;
    context
        .push('/status/view',
            extra: StatusViewerArgs([
              StatusUser(userId: core.userId, name: 'My status', avatarPath: me?.avatarPath, avatarVersion: me?.avatarVersion ?? 0, items: mine, mine: true),
            ], 0))
        .then((_) => _load());
  }

  void _open(List<StatusUser> list, int i) {
    context.push('/status/view', extra: StatusViewerArgs(list, i)).then((_) => _load());
  }

  @override
  Widget build(BuildContext context) {
    final me = ref.watch(sessionProvider).profile;
    final f = feed;
    final recent = f?.where((u) => !u.muted && !u.allViewed).toList() ?? [];
    final viewed = f?.where((u) => !u.muted && u.allViewed).toList() ?? [];
    final muted = f?.where((u) => u.muted).toList() ?? [];
    return Scaffold(
      appBar: AppBar(title: const Text('Updates'), actions: [
        IconButton(tooltip: 'Status privacy', icon: const Icon(Icons.lock_person_outlined), onPressed: () => context.push('/status/privacy')),
      ]),
      floatingActionButton: Column(mainAxisSize: MainAxisSize.min, children: [
        FloatingActionButton.small(
          heroTag: 'status-text',
          tooltip: 'Text status',
          onPressed: () => context.push('/status/compose').then((_) => _load()),
          child: const Icon(Icons.edit_rounded),
        ),
        const SizedBox(height: 12),
        FloatingActionButton(
          heroTag: 'status-media',
          tooltip: 'Photo or video status',
          onPressed: posting ? null : _addMedia,
          child: posting ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4)) : const Icon(Icons.photo_camera_rounded),
        ),
      ]),
      body: error != null && f == null
          ? ErrorState(error: error!, onRetry: _load)
          : f == null
              ? const ListSkeleton(count: 5)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.only(bottom: 140), children: [
                    ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      leading: _Ring(
                        segments: mine.length,
                        seen: true,
                        child: Stack(clipBehavior: Clip.none, children: [
                          HimeAvatar(name: me?.name ?? 'Me', path: me?.avatarPath, version: me?.avatarVersion ?? 0, size: 50),
                          if (mine.isEmpty)
                            Positioned(
                              right: -2,
                              bottom: -2,
                              child: Container(
                                decoration: BoxDecoration(color: HimeColors.yellow, shape: BoxShape.circle, border: Border.all(color: context.colors.surface, width: 2)),
                                child: const Icon(Icons.add_rounded, size: 18, color: HimeColors.ink),
                              ),
                            ),
                        ]),
                      ),
                      title: const Text('My status', style: TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Text(mine.isEmpty ? 'Tap to add a status update' : '${mine.length} update(s) · ${Fmt.chatTime(mine.last.createdAt)}'),
                      onTap: _openMine,
                    ),
                    if (recent.isEmpty && viewed.isEmpty && muted.isEmpty)
                      const Padding(
                        padding: EdgeInsets.all(32),
                        child: Text('Status updates from your contacts appear here and disappear after 24 hours.', textAlign: TextAlign.center),
                      ),
                    if (recent.isNotEmpty) _section('Recent updates'),
                    for (final u in recent) _userTile(recent, u),
                    if (viewed.isNotEmpty) _section('Viewed updates'),
                    for (final u in viewed) _userTile(viewed, u),
                    if (muted.isNotEmpty)
                      ListTile(
                        title: Text('Muted updates (${muted.length})', style: context.text.labelLarge?.copyWith(color: context.palette.muted)),
                        trailing: Icon(showMuted ? Icons.expand_less_rounded : Icons.expand_more_rounded),
                        onTap: () => setState(() => showMuted = !showMuted),
                      ),
                    if (showMuted)
                      for (final u in muted) Opacity(opacity: 0.6, child: _userTile(muted, u)),
                  ]),
                ),
    );
  }

  Widget _section(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 4),
        child: Text(t, style: context.text.labelLarge?.copyWith(color: context.palette.muted, fontWeight: FontWeight.w600)),
      );

  Widget _userTile(List<StatusUser> list, StatusUser u) => ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        leading: _Ring(
          segments: u.items.length,
          seen: u.allViewed,
          child: HimeAvatar(name: u.name, path: u.avatarPath, version: u.avatarVersion, size: 50),
        ),
        title: Text(u.name, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(Fmt.chatTime(u.latest)),
        onTap: () => _open(list, list.indexOf(u)),
        onLongPress: () => showActionSheet(context, title: u.name, actions: [
          SheetAction(u.muted ? Icons.volume_up_outlined : Icons.volume_off_outlined, u.muted ? 'Unmute status updates' : 'Mute status updates', () async {
            await guard(context, () => repo.setMuted(u.userId, !u.muted));
            await _load();
          }),
          SheetAction(Icons.person_outline_rounded, 'View profile', () => context.push('/user/${u.userId}')),
        ]),
      );
}

/// Segmented ring around a status avatar.
class _Ring extends StatelessWidget {
  const _Ring({required this.segments, required this.seen, required this.child});
  final int segments;
  final bool seen;
  final Widget child;

  @override
  Widget build(BuildContext context) => CustomPaint(
        painter: _RingPainter(segments, seen ? context.palette.border : HimeColors.yellowDeep),
        child: Padding(padding: const EdgeInsets.all(4), child: child),
      );
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.segments, this.color);
  final int segments;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    if (segments <= 0) return;
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.6
      ..strokeCap = StrokeCap.round;
    final rect = Offset.zero & size;
    final r = rect.deflate(1.3);
    final gap = segments == 1 ? 0.0 : 0.18;
    final sweep = (2 * math.pi - gap * segments) / segments;
    for (var i = 0; i < segments; i++) {
      canvas.drawArc(r, -math.pi / 2 + i * (sweep + gap) + gap / 2, sweep, false, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) => old.segments != segments || old.color != color;
}

// ---------------------------------------------------------------- compose

class TextStatusComposer extends ConsumerStatefulWidget {
  const TextStatusComposer({super.key});

  @override
  ConsumerState<TextStatusComposer> createState() => _TextStatusComposerState();
}

class _TextStatusComposerState extends ConsumerState<TextStatusComposer> {
  static const _colors = [
    Color(0xFF202124),
    Color(0xFFE2BC1F),
    Color(0xFF2EB872),
    Color(0xFF2F80ED),
    Color(0xFF8E5BD8),
    Color(0xFFE5486A),
    Color(0xFFEF7B45),
    Color(0xFF16A6B6),
  ];
  final _text = TextEditingController();
  int color = 1;
  int font = 0;
  bool posting = false;

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  Future<void> _post() async {
    final body = _text.text.trim();
    if (body.isEmpty) return;
    setState(() => posting = true);
    final ok = await guard(context, () => StatusRepo(ref.read(coreProvider)).postText(body, colorHex(_colors[color]), font));
    if (!mounted) return;
    setState(() => posting = false);
    if (ok) context.pop();
  }

  @override
  Widget build(BuildContext context) {
    final bg = _colors[color];
    final fg = bg.computeLuminance() > 0.5 ? HimeColors.ink : Colors.white;
    return Scaffold(
      backgroundColor: bg,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        foregroundColor: fg,
        actions: [
          IconButton(tooltip: 'Font', icon: const Icon(Icons.text_fields_rounded), onPressed: () => setState(() => font = (font + 1) % 5)),
          IconButton(tooltip: 'Colour', icon: const Icon(Icons.palette_outlined), onPressed: () => setState(() => color = (color + 1) % _colors.length)),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: posting ? null : _post,
        backgroundColor: fg == Colors.white ? HimeColors.yellow : HimeColors.ink,
        foregroundColor: fg == Colors.white ? HimeColors.ink : Colors.white,
        child: posting ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4)) : const Icon(Icons.send_rounded),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: TextField(
            controller: _text,
            autofocus: true,
            maxLength: 700,
            maxLines: null,
            textAlign: TextAlign.center,
            cursorColor: fg,
            style: statusFont(font).copyWith(color: fg, fontSize: 30, height: 1.3),
            decoration: InputDecoration(
              hintText: 'Type a status',
              hintStyle: TextStyle(color: fg.withValues(alpha: 0.6), fontSize: 30),
              filled: false,
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              counterStyle: TextStyle(color: fg.withValues(alpha: 0.7)),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- viewer

class StatusViewerScreen extends ConsumerStatefulWidget {
  const StatusViewerScreen({super.key, required this.args});
  final StatusViewerArgs args;

  @override
  ConsumerState<StatusViewerScreen> createState() => _StatusViewerScreenState();
}

class _StatusViewerScreenState extends ConsumerState<StatusViewerScreen> with SingleTickerProviderStateMixin {
  late final HimeCore core = ref.read(coreProvider);
  late final repo = StatusRepo(core);
  late int userIndex = widget.args.index;
  int itemIndex = 0;
  late final AnimationController _progress = AnimationController(vsync: this);
  VideoPlayerController? _video;
  String? _imageUrl;
  bool _ready = false;
  bool _loadScheduled = false;
  final _reply = TextEditingController();
  final _replyFocus = FocusNode();

  StatusUser get user => widget.args.users[userIndex];
  StatusItem get item => user.items[itemIndex];

  @override
  void initState() {
    super.initState();
    _progress.addStatusListener((s) {
      if (s == AnimationStatus.completed) _next();
    });
    _replyFocus.addListener(() {
      if (_replyFocus.hasFocus) {
        _pause();
      } else {
        _resume();
      }
    });
    final firstUnseen = user.items.indexWhere((i) => !i.viewed);
    itemIndex = user.mine || firstUnseen < 0 ? 0 : firstUnseen;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _show();
    });
  }

  @override
  void dispose() {
    _progress.dispose();
    _video?.dispose();
    _reply.dispose();
    _replyFocus.dispose();
    super.dispose();
  }

  Future<void> _show() async {
    _progress.stop();
    _progress.value = 0;
    final old = _video;
    _video = null;
    unawaited(old?.dispose());
    setState(() {
      _ready = false;
      _loadScheduled = false;
      _imageUrl = null;
    });
    final s = item;
    if (!user.mine && !s.viewed) {
      s.viewed = true;
      unawaited(core.sb.rpc('mark_status_viewed', params: {'p_status_id': s.id}).then((_) {}, onError: (_) {}));
    }
    if (s.kind == 'text') {
      _progress.duration = Duration(milliseconds: (4000 + (s.body?.length ?? 0) * 40).clamp(4000, 10000));
      setState(() => _ready = true);
      _progress.forward();
      return;
    }
    final url = await SignedUrls.get('status', s.mediaPath!, ttlSeconds: 600);
    if (!mounted || item != s) return;
    if (url == null) {
      _progress.duration = const Duration(seconds: 3);
      setState(() => _ready = true);
      _progress.forward();
      return;
    }
    if (s.kind == 'video') {
      final vc = VideoPlayerController.networkUrl(Uri.parse(url));
      _video = vc;
      try {
        await vc.initialize();
        if (!mounted || _video != vc) return;
        _progress.duration = vc.value.duration.inMilliseconds > 0 ? vc.value.duration : Duration(milliseconds: s.durationMs ?? 15000);
        setState(() => _ready = true);
        await vc.play();
        _progress.forward();
      } catch (_) {
        if (mounted) _next();
      }
    } else {
      setState(() => _imageUrl = url);
    }
  }

  void _imageLoaded() {
    if (_ready || _loadScheduled) return;
    _loadScheduled = true;
    _progress.duration = const Duration(seconds: 6);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      setState(() => _ready = true);
      _progress.forward();
    });
  }

  void _pause() {
    _progress.stop();
    _video?.pause();
  }

  void _resume() {
    if (!_ready || _replyFocus.hasFocus) return;
    _progress.forward();
    _video?.play();
  }

  void _next() {
    if (itemIndex < user.items.length - 1) {
      itemIndex++;
      _show();
    } else if (userIndex < widget.args.users.length - 1) {
      userIndex++;
      final firstUnseen = user.items.indexWhere((i) => !i.viewed);
      itemIndex = firstUnseen < 0 ? 0 : firstUnseen;
      _show();
    } else {
      context.pop();
    }
  }

  void _prev() {
    if (itemIndex > 0) {
      itemIndex--;
      _show();
    } else if (userIndex > 0) {
      userIndex--;
      itemIndex = 0;
      _show();
    } else {
      _show();
    }
  }

  Future<void> _sendReply({String? emoji}) async {
    final text = emoji ?? _reply.text.trim();
    if (text.isEmpty) return;
    final s = item;
    final u = user;
    _reply.clear();
    _replyFocus.unfocus();
    try {
      if (emoji != null) {
        await core.sb.rpc('mark_status_viewed', params: {'p_status_id': s.id, 'p_reaction': emoji});
      }
      final conv = await core.sb.rpc('get_or_create_direct', params: {'p_other': u.userId}) as String;
      final preview = s.kind == 'text' ? (s.body ?? '') : (s.kind == 'video' ? '🎥 Status' : '📷 Status');
      await core.chats.sendText(conv, text, reply: {'id': s.id, 'sender': u.userId, 'preview': 'Status · $preview', 'status': true});
      if (mounted) toast(context, emoji != null ? 'Reaction sent' : 'Reply sent');
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
  }

  Future<void> _viewers() async {
    _pause();
    final s = item;
    try {
      final rows = (await core.sb.rpc('get_status_viewers', params: {'p_status_id': s.id}) as List<dynamic>).cast<Map<String, dynamic>>();
      if (!mounted) return;
      await showModalBottomSheet<void>(
        context: context,
        builder: (ctx) => SafeArea(
          child: SizedBox(
            height: 360,
            child: Column(children: [
              Padding(padding: const EdgeInsets.all(12), child: Text('Viewed by ${rows.length}', style: ctx.text.titleMedium)),
              Expanded(
                child: rows.isEmpty
                    ? Center(child: Text('No views yet', style: TextStyle(color: ctx.palette.muted)))
                    : ListView(children: [
                        for (final r in rows)
                          ListTile(
                            leading: HimeAvatar(
                              name: (r['display_name'] as String?) ?? '',
                              path: r['avatar_path'] as String?,
                              version: (r['avatar_version'] as num?)?.toInt() ?? 0,
                              size: 40,
                            ),
                            title: Text((r['display_name'] as String?) ?? 'Hime user'),
                            subtitle: Text(Fmt.chatTime(parseTime(r['viewed_at']) ?? DateTime.now())),
                            trailing: r['reaction'] == null ? null : Text(r['reaction'] as String, style: const TextStyle(fontSize: 22)),
                          ),
                      ]),
              ),
            ]),
          ),
        ),
      );
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    _resume();
  }

  Future<void> _delete() async {
    _pause();
    final ok = await confirm(context, title: 'Delete this status update?', confirmLabel: 'Delete', danger: true);
    if (!ok || !mounted) {
      _resume();
      return;
    }
    final s = item;
    final done = await guard(context, () => repo.delete(s));
    if (!done || !mounted) {
      _resume();
      return;
    }
    user.items.remove(s);
    if (user.items.isEmpty) {
      context.pop();
      return;
    }
    if (itemIndex >= user.items.length) itemIndex = user.items.length - 1;
    _show();
  }

  @override
  Widget build(BuildContext context) {
    final s = item;
    final u = user;
    Widget content;
    if (s.kind == 'text') {
      final bg = hexColor(s.background);
      final fg = bg.computeLuminance() > 0.5 ? HimeColors.ink : Colors.white;
      content = Container(
        color: bg,
        alignment: Alignment.center,
        padding: const EdgeInsets.all(32),
        child: Text(s.body ?? '', textAlign: TextAlign.center, style: statusFont(s.font).copyWith(color: fg, fontSize: 30, height: 1.3)),
      );
    } else if (s.kind == 'video') {
      final v = _video;
      content = v != null && v.value.isInitialized
          ? Center(child: AspectRatio(aspectRatio: v.value.aspectRatio, child: VideoPlayer(v)))
          : const Center(child: CircularProgressIndicator(color: Colors.white));
    } else {
      content = _imageUrl == null
          ? const Center(child: CircularProgressIndicator(color: Colors.white))
          : Image.network(
              _imageUrl!,
              fit: BoxFit.contain,
              width: double.infinity,
              height: double.infinity,
              frameBuilder: (context, child, frame, sync) {
                if (frame != null || sync) _imageLoaded();
                return child;
              },
              loadingBuilder: (context, child, progress) =>
                  progress == null ? child : const Center(child: CircularProgressIndicator(color: Colors.white)),
              errorBuilder: (_, __, ___) {
                _imageLoaded();
                return const Center(child: Icon(Icons.broken_image_outlined, color: Colors.white54, size: 64));
              },
            );
    }
    return Scaffold(
      backgroundColor: Colors.black,
      resizeToAvoidBottomInset: true,
      body: GestureDetector(
        onLongPressStart: (_) => _pause(),
        onLongPressEnd: (_) => _resume(),
        onVerticalDragEnd: (d) {
          if ((d.primaryVelocity ?? 0) > 300) context.pop();
        },
        onTapUp: (d) {
          final w = MediaQuery.of(context).size.width;
          if (d.globalPosition.dx < w * 0.3) {
            _prev();
          } else {
            _next();
          }
        },
        child: Stack(children: [
          Positioned.fill(child: content),
          if ((s.caption ?? '').isNotEmpty)
            Positioned(
              left: 0,
              right: 0,
              bottom: 96,
              child: Container(
                color: Colors.black45,
                padding: const EdgeInsets.all(14),
                child: Text(s.caption!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 15)),
              ),
            ),
          SafeArea(
            child: Column(children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
                child: Row(children: [
                  for (var i = 0; i < u.items.length; i++)
                    Expanded(
                      child: Container(
                        height: 3,
                        margin: const EdgeInsets.symmetric(horizontal: 2),
                        decoration: BoxDecoration(color: Colors.white30, borderRadius: BorderRadius.circular(2)),
                        child: i < itemIndex
                            ? Container(color: Colors.white)
                            : i == itemIndex
                                ? AnimatedBuilder(
                                    animation: _progress,
                                    builder: (_, __) => FractionallySizedBox(
                                      alignment: Alignment.centerLeft,
                                      widthFactor: _progress.value,
                                      child: Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(2))),
                                    ),
                                  )
                                : null,
                      ),
                    ),
                ]),
              ),
              ListTile(
                leading: HimeAvatar(name: u.name, path: u.avatarPath, version: u.avatarVersion, size: 40),
                title: Text(u.name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                subtitle: Text(Fmt.chatTime(s.createdAt), style: const TextStyle(color: Colors.white70)),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  if (u.mine) IconButton(color: Colors.white, icon: const Icon(Icons.delete_outline_rounded), onPressed: _delete),
                  IconButton(color: Colors.white, icon: const Icon(Icons.close_rounded), onPressed: () => context.pop()),
                ]),
              ),
              const Spacer(),
              if (u.mine)
                TextButton.icon(
                  onPressed: _viewers,
                  icon: const Icon(Icons.visibility_outlined, color: Colors.white),
                  label: const Text('Viewers', style: TextStyle(color: Colors.white)),
                )
              else
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                  child: Column(children: [
                    Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                      for (final e in quickReactions.take(5))
                        GestureDetector(
                          onTap: () => _sendReply(emoji: e),
                          child: Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: Text(e, style: const TextStyle(fontSize: 26))),
                        ),
                    ]),
                    const SizedBox(height: 10),
                    Row(children: [
                      Expanded(
                        child: TextField(
                          controller: _reply,
                          focusNode: _replyFocus,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            hintText: 'Reply…',
                            hintStyle: const TextStyle(color: Colors.white70),
                            filled: true,
                            fillColor: Colors.white.withValues(alpha: 0.12),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                            focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                          ),
                          onSubmitted: (_) => _sendReply(),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton.filled(
                        style: IconButton.styleFrom(backgroundColor: HimeColors.yellow, foregroundColor: HimeColors.ink),
                        onPressed: () => _sendReply(),
                        icon: const Icon(Icons.send_rounded),
                      ),
                    ]),
                  ]),
                ),
            ]),
          ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- privacy

class StatusPrivacyScreen extends ConsumerStatefulWidget {
  const StatusPrivacyScreen({super.key});

  @override
  ConsumerState<StatusPrivacyScreen> createState() => _StatusPrivacyScreenState();
}

class _StatusPrivacyScreenState extends ConsumerState<StatusPrivacyScreen> {
  late final HimeCore core = ref.read(coreProvider);
  String? audience;
  List<String> except = [];
  List<String> only = [];
  bool saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await core.sb.from('user_privacy_settings').select('status_audience').eq('user_id', core.userId).maybeSingle();
      final rows = await core.sb.from('status_audience_list').select('list_kind, member_id').eq('user_id', core.userId);
      if (!mounted) return;
      setState(() {
        audience = (s?['status_audience'] as String?) ?? 'contacts';
        except = rows.where((r) => r['list_kind'] == 'except').map((r) => r['member_id'] as String).toList();
        only = rows.where((r) => r['list_kind'] == 'only').map((r) => r['member_id'] as String).toList();
      });
    } catch (e) {
      if (mounted) {
        toast(context, friendlyError(e));
        setState(() => audience = 'contacts');
      }
    }
  }

  Future<List<String>?> _pick(List<String> current) async {
    final repo = ContactsRepo(core);
    final initial = await repo.profiles(current);
    if (!mounted) return null;
    List<Profile> chosen = initial;
    final ok = await Navigator.of(context).push<bool>(MaterialPageRoute(
      builder: (ctx) => Scaffold(
        appBar: AppBar(title: const Text('Choose contacts'), actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Done')),
        ]),
        body: PeoplePicker(core: core, multi: true, initial: initial, onSelectionChanged: (s) => chosen = s),
      ),
    ));
    if (ok != true) return null;
    return chosen.map((p) => p.id).toList();
  }

  Future<void> _set(String value) async {
    List<String>? list;
    if (value == 'contacts_except') list = await _pick(except);
    if (value == 'only_share_with') list = await _pick(only);
    if (value != 'contacts' && list == null) return;
    setState(() => saving = true);
    final kind = value == 'contacts_except' ? 'except' : 'only';
    final members = list;
    final ok = await guard(context, () async {
      if (members != null) {
        await core.sb.from('status_audience_list').delete().eq('user_id', core.userId).eq('list_kind', kind);
        if (members.isNotEmpty) {
          await core.sb.from('status_audience_list').insert([
            for (final id in members) {'user_id': core.userId, 'list_kind': kind, 'member_id': id},
          ]);
        }
      }
      await core.sb.from('user_privacy_settings').update({'status_audience': value}).eq('user_id', core.userId);
    });
    if (ok && mounted) await _load();
    if (mounted) setState(() => saving = false);
  }

  @override
  Widget build(BuildContext context) {
    final a = audience;
    Widget option(String value, String title, String? subtitle) => ListTile(
          leading: Icon(a == value ? Icons.radio_button_checked_rounded : Icons.radio_button_unchecked_rounded,
              color: a == value ? HimeColors.yellowDeep : context.palette.muted),
          title: Text(title),
          subtitle: subtitle == null ? null : Text(subtitle),
          onTap: saving ? null : () => _set(value),
        );
    return Scaffold(
      appBar: AppBar(title: const Text('Status privacy')),
      body: a == null
          ? const CenteredLoader()
          : ListView(children: [
              Padding(
                padding: const EdgeInsets.all(20),
                child: Text('Who can see my status updates', style: context.text.titleSmall),
              ),
              option('contacts', 'My contacts', null),
              option('contacts_except', 'My contacts except…', except.isEmpty ? null : '${except.length} excluded'),
              option('only_share_with', 'Only share with…', only.isEmpty ? null : '${only.length} included'),
              if (saving) const LinearProgressIndicator(minHeight: 2),
              Padding(
                padding: const EdgeInsets.all(20),
                child: Text(
                  'Changes to your privacy settings won\'t affect status updates you\'ve already sent. Status updates disappear after 24 hours.',
                  style: context.text.bodySmall?.copyWith(color: context.palette.muted),
                ),
              ),
            ]),
    );
  }
}
