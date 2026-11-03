import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import 'chat_list_screen.dart';
import 'extra_screens.dart';
import 'models.dart';

const quickReactions = ['❤️', '😂', '👍', '😮', '😢', '🙏'];

/// One message row: bubble, reply quote, media, reactions, time and ticks.
class MessageBubble extends StatefulWidget {
  const MessageBubble({
    super.key,
    required this.message,
    required this.core,
    required this.isMine,
    required this.delivery,
    required this.showSender,
    required this.groupedWithNext,
    this.reactions,
    this.starred = false,
    this.onLongPress,
    this.onReply,
    this.onRetry,
    this.highlight = false,
  });

  final ChatMessage message;
  final HimeCore core;
  final bool isMine;
  final Delivery delivery;
  final bool showSender;
  final bool groupedWithNext;
  final Map<String, String>? reactions;
  final bool starred;
  final VoidCallback? onLongPress;
  final VoidCallback? onReply;
  final VoidCallback? onRetry;
  final bool highlight;

  @override
  State<MessageBubble> createState() => _MessageBubbleState();
}

class _MessageBubbleState extends State<MessageBubble> {
  double _drag = 0;

  @override
  Widget build(BuildContext context) {
    final m = widget.message;
    if (m.isSystem) return SystemNotice(text: ChatMessage.systemLabel(m.system, (id) => widget.core.profiles.nameOf(id)));
    final mine = widget.isMine;
    final palette = context.palette;
    final bg = mine ? palette.outgoingBubble : palette.incomingBubble;
    final fg = mine ? palette.onOutgoingBubble : palette.onIncomingBubble;
    final radius = BorderRadius.only(
      topLeft: const Radius.circular(HimeRadius.bubble),
      topRight: const Radius.circular(HimeRadius.bubble),
      bottomLeft: Radius.circular(mine || widget.groupedWithNext ? HimeRadius.bubble : 4),
      bottomRight: Radius.circular(!mine || widget.groupedWithNext ? HimeRadius.bubble : 4),
    );
    final maxWidth = MediaQuery.sizeOf(context).width * 0.78;
    final reactions = widget.reactions ?? const {};
    final counts = <String, int>{};
    for (final e in reactions.values) {
      counts[e] = (counts[e] ?? 0) + 1;
    }

    Widget content = _content(context, fg);
    final bubble = Container(
      constraints: BoxConstraints(maxWidth: maxWidth),
      decoration: BoxDecoration(
        color: widget.highlight ? HimeColors.yellow.withValues(alpha: 0.35) : bg,
        borderRadius: radius,
        border: mine || context.isDark ? null : Border.all(color: palette.border),
      ),
      padding: const EdgeInsets.fromLTRB(10, 7, 10, 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        if (widget.showSender && !mine)
          Padding(
            padding: const EdgeInsets.only(bottom: 3),
            child: Text(widget.core.profiles.nameOf(m.senderId),
                style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: _nameColor(m.senderId ?? ''))),
          ),
        if (m.forwarded && !m.isDeleted)
          Padding(
            padding: const EdgeInsets.only(bottom: 3),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.shortcut_rounded, size: 14, color: palette.muted),
              const SizedBox(width: 3),
              Text('Forwarded', style: context.text.labelSmall?.copyWith(fontStyle: FontStyle.italic)),
            ]),
          ),
        if (m.reply != null && !m.isDeleted) _ReplyQuote(reply: m.reply!, core: widget.core),
        content,
        const SizedBox(height: 2),
        Align(
          alignment: Alignment.bottomRight,
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            if (widget.starred) Icon(Icons.star_rounded, size: 12, color: palette.muted),
            if (m.editedAt != null && !m.isDeleted) Text('edited · ', style: context.text.labelSmall?.copyWith(fontSize: 10.5)),
            Text(Fmt.time(m.createdAt), style: context.text.labelSmall?.copyWith(fontSize: 10.5)),
            if (mine) ...[const SizedBox(width: 3), DeliveryTicks(state: widget.delivery, size: 14)],
          ]),
        ),
      ]),
    );

    final row = Padding(
      padding: EdgeInsets.only(left: 10, right: 10, top: 1.5, bottom: widget.groupedWithNext ? 1.5 : 6),
      child: Column(crossAxisAlignment: mine ? CrossAxisAlignment.end : CrossAxisAlignment.start, children: [
        Row(mainAxisAlignment: mine ? MainAxisAlignment.end : MainAxisAlignment.start, children: [
          if (mine && m.localState == 2)
            IconButton(
              tooltip: 'Retry',
              onPressed: widget.onRetry,
              icon: Icon(Icons.refresh_rounded, color: context.colors.error),
            ),
          Flexible(child: bubble),
        ]),
        if (counts.isNotEmpty)
          Transform.translate(
            offset: const Offset(0, -4),
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 8),
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(
                color: context.colors.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: palette.border),
              ),
              child: Text(
                counts.entries.map((e) => e.value > 1 ? '${e.key}${e.value}' : e.key).join(' '),
                style: const TextStyle(fontSize: 13),
              ),
            ),
          ),
      ]),
    );

    return GestureDetector(
      onLongPress: widget.onLongPress == null
          ? null
          : () {
              HapticFeedback.selectionClick();
              widget.onLongPress!();
            },
      onHorizontalDragUpdate: m.isDeleted || widget.onReply == null
          ? null
          : (d) => setState(() => _drag = (_drag + d.delta.dx).clamp(0.0, 80.0)),
      onHorizontalDragEnd: (_) {
        if (_drag > 56) {
          HapticFeedback.lightImpact();
          widget.onReply?.call();
        }
        setState(() => _drag = 0);
      },
      child: Stack(children: [
        if (_drag > 8)
          Positioned(
            left: 12,
            top: 0,
            bottom: 0,
            child: Opacity(opacity: (_drag / 56).clamp(0.0, 1.0), child: const Icon(Icons.reply_rounded)),
          ),
        AnimatedContainer(
          duration: Duration(milliseconds: _drag == 0 ? 180 : 0),
          transform: Matrix4.translationValues(_drag, 0, 0),
          child: row,
        ),
      ]),
    );
  }

  Widget _content(BuildContext context, Color fg) {
    final m = widget.message;
    final textStyle = context.text.bodyLarge?.copyWith(color: fg, fontSize: 15.5);
    if (m.isDeleted) {
      return Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.block_rounded, size: 15, color: context.palette.muted),
        const SizedBox(width: 6),
        Text(widget.isMine ? 'You deleted this message' : 'This message was deleted',
            style: textStyle?.copyWith(fontStyle: FontStyle.italic, color: context.palette.muted)),
      ]);
    }
    if (m.undecryptable) {
      return Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.lock_clock_rounded, size: 15, color: context.palette.muted),
        const SizedBox(width: 6),
        Flexible(
          child: Text('Waiting for this message. It was encrypted before this phone joined.',
              style: textStyle?.copyWith(fontStyle: FontStyle.italic, color: context.palette.muted, fontSize: 13.5)),
        ),
      ]);
    }
    if (m.isCall) {
      final video = m.system?['media'] == 'video';
      final missed = !{'ended'}.contains(m.system?['status']);
      return Row(mainAxisSize: MainAxisSize.min, children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: context.colors.surfaceContainer, shape: BoxShape.circle),
          child: Icon(video ? Icons.videocam_rounded : Icons.call_rounded, size: 18, color: missed ? context.colors.error : fg),
        ),
        const SizedBox(width: 10),
        Flexible(child: Text(ChatMessage.callLabel(m.system).replaceAll(RegExp(r'^\S+ '), ''), style: textStyle)),
      ]);
    }
    final children = <Widget>[];
    switch (m.kind) {
      case 'image':
      case 'video':
        children.add(MediaThumb(message: m, core: widget.core));
      case 'voice':
      case 'audio':
        children.add(VoiceMessage(message: m, core: widget.core, color: fg));
      case 'document':
        children.add(DocumentTile(message: m, core: widget.core));
      case 'contact':
        children.add(_ContactCard(data: (m.payload?['contact'] as Map?)?.cast<String, dynamic>() ?? {}));
      case 'location':
        children.add(_LocationCard(data: (m.payload?['location'] as Map?)?.cast<String, dynamic>() ?? {}));
    }
    final link = m.payload?['link'];
    if (link is Map) children.add(LinkPreviewCard(data: link.cast<String, dynamic>()));
    if (m.text.isNotEmpty) {
      children.add(Padding(
        padding: EdgeInsets.only(top: children.isEmpty ? 0 : 6),
        child: LinkifiedText(text: m.text, style: textStyle),
      ));
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: children);
  }

  static Color _nameColor(String id) {
    const colors = [Color(0xFFC2185B), Color(0xFF6A1B9A), Color(0xFF1565C0), Color(0xFF00838F), Color(0xFF2E7D32), Color(0xFFEF6C00), Color(0xFF5D4037)];
    return colors[id.hashCode.abs() % colors.length];
  }
}

class SystemNotice extends StatelessWidget {
  const SystemNotice({super.key, required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Center(
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 40),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: context.colors.surface.withValues(alpha: 0.92),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: context.palette.border),
          ),
          child: Text(text, textAlign: TextAlign.center, style: context.text.labelMedium),
        ),
      );
}

class DateChip extends StatelessWidget {
  const DateChip({super.key, required this.date});
  final DateTime date;

  @override
  Widget build(BuildContext context) => Center(
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 10),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
          decoration: BoxDecoration(color: context.colors.surface, borderRadius: BorderRadius.circular(10)),
          child: Text(Fmt.dayLabel(date), style: context.text.labelMedium?.copyWith(fontWeight: FontWeight.w600)),
        ),
      );
}

class _ReplyQuote extends StatelessWidget {
  const _ReplyQuote({required this.reply, required this.core});
  final Map<String, dynamic> reply;
  final HimeCore core;

  @override
  Widget build(BuildContext context) {
    final who = reply['sender'] == core.userId ? 'You' : core.profiles.nameOf(reply['sender'] as String?);
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
      decoration: BoxDecoration(
        color: context.colors.onSurface.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(10),
        border: const Border(left: BorderSide(color: HimeColors.yellowDeep, width: 3)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(who, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: HimeColors.yellowDeep)),
        const SizedBox(height: 2),
        Text('${reply['preview'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis, style: context.text.bodySmall),
      ]),
    );
  }
}

/// Text with tappable links.
class LinkifiedText extends StatelessWidget {
  const LinkifiedText({super.key, required this.text, this.style});
  final String text;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    final spans = <TextSpan>[];
    var last = 0;
    for (final match in urlRegex.allMatches(text)) {
      if (match.start > last) spans.add(TextSpan(text: text.substring(last, match.start)));
      final url = match.group(0)!;
      spans.add(TextSpan(
        text: url,
        style: const TextStyle(color: HimeColors.read, decoration: TextDecoration.underline),
        recognizer: null,
        mouseCursor: SystemMouseCursors.click,
      ));
      last = match.end;
    }
    if (last < text.length) spans.add(TextSpan(text: text.substring(last)));
    final hasLinks = spans.length > 1 || urlRegex.hasMatch(text);
    final rich = Text.rich(TextSpan(style: style, children: spans));
    if (!hasLinks) return rich;
    return GestureDetector(
      onTap: () {
        final url = findUrls(text).first;
        launchUrl(Uri.parse(url.startsWith('http') ? url : 'https://$url'), mode: LaunchMode.externalApplication);
      },
      child: rich,
    );
  }
}

/// Image/video bubble content with download progress and blur placeholder.
class MediaThumb extends StatefulWidget {
  const MediaThumb({super.key, required this.message, required this.core});
  final ChatMessage message;
  final HimeCore core;

  @override
  State<MediaThumb> createState() => _MediaThumbState();
}

class _MediaThumbState extends State<MediaThumb> {
  File? _file;
  bool _loading = false;
  Object? _error;

  @override
  void initState() {
    super.initState();
    final size = (widget.message.media?['size'] as num?)?.toInt() ?? 0;
    // Auto-download small images (privacy: media is only fetched on demand otherwise).
    if (widget.message.kind == 'image' && size < 2 * 1024 * 1024) _load();
    if (widget.message.localState != 0) _load();
  }

  Future<void> _load() async {
    if (_loading) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final f = await widget.core.chats.mediaFile(widget.message);
      if (mounted) setState(() => _file = f);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final media = widget.message.media ?? {};
    final w = (media['w'] as num?)?.toDouble() ?? 4;
    final h = (media['h'] as num?)?.toDouble() ?? 3;
    final aspect = (w / h).clamp(0.6, 1.8);
    final thumb = media['thumb'] as String?;
    final isVideo = widget.message.kind == 'video';
    final bar = widget.core.chats.progress[widget.message.id];
    Widget preview;
    if (_file != null && !isVideo) {
      preview = Image.file(_file!, fit: BoxFit.cover, cacheWidth: 720, gaplessPlayback: true);
    } else if (thumb != null) {
      preview = Image.memory(base64Decode(thumb), fit: BoxFit.cover, filterQuality: FilterQuality.low, gaplessPlayback: true);
    } else {
      preview = Container(color: context.colors.surfaceContainerHigh);
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: SizedBox(
        width: 240,
        child: AspectRatio(
          aspectRatio: aspect,
          child: Stack(fit: StackFit.expand, children: [
            Hero(tag: 'media-${widget.message.id}', child: preview),
            if (_file == null || isVideo)
              Center(
                child: GestureDetector(
                  onTap: _file != null ? _open : _load,
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: const BoxDecoration(color: Colors.black45, shape: BoxShape.circle),
                    child: _loading || widget.message.localState == 1
                        ? SizedBox(
                            width: 30,
                            height: 30,
                            child: bar == null
                                ? const CircularProgressIndicator(strokeWidth: 2.6, color: Colors.white)
                                : ValueListenableBuilder<double>(
                                    valueListenable: bar,
                                    builder: (_, v, __) =>
                                        CircularProgressIndicator(value: v.clamp(0.02, 1.0), strokeWidth: 2.6, color: Colors.white),
                                  ),
                          )
                        : Icon(
                            _error != null
                                ? Icons.refresh_rounded
                                : (_file != null ? Icons.play_arrow_rounded : Icons.download_rounded),
                            color: Colors.white,
                            size: 30,
                          ),
                  ),
                ),
              ),
            if (_file != null && !isVideo) Positioned.fill(child: Material(color: Colors.transparent, child: InkWell(onTap: _open))),
            if (media['size'] != null && _file == null)
              Positioned(
                left: 8,
                bottom: 8,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(8)),
                  child: Text(Fmt.bytes((media['size'] as num).toInt()), style: const TextStyle(color: Colors.white, fontSize: 11)),
                ),
              ),
          ]),
        ),
      ),
    );
  }

  void _open() {
    if (_file == null) return;
    context.push('/viewer',
        extra: MediaViewerArgs(file: _file!, isVideo: widget.message.kind == 'video', heroTag: 'media-${widget.message.id}', caption: widget.message.text));
  }
}

/// Voice note / audio player with waveform.
class VoiceMessage extends StatefulWidget {
  const VoiceMessage({super.key, required this.message, required this.core, required this.color});
  final ChatMessage message;
  final HimeCore core;
  final Color color;

  @override
  State<VoiceMessage> createState() => _VoiceMessageState();
}

class _VoiceMessageState extends State<VoiceMessage> {
  AudioPlayer? _player;
  bool _loading = false;
  Duration _pos = Duration.zero;
  Duration? _dur;
  bool _playing = false;
  final _subs = <StreamSubscription<dynamic>>[];

  Future<void> _toggle() async {
    if (_player != null) {
      _playing ? await _player!.pause() : await _player!.play();
      return;
    }
    setState(() => _loading = true);
    try {
      final f = await widget.core.chats.mediaFile(widget.message);
      if (f == null) throw StateError('missing');
      final p = AudioPlayer();
      _player = p;
      _dur = await p.setFilePath(f.path);
      _subs.add(p.positionStream.listen((d) => mounted ? setState(() => _pos = d) : null));
      _subs.add(p.playerStateStream.listen((s) {
        if (!mounted) return;
        setState(() => _playing = s.playing && s.processingState != ProcessingState.completed);
        if (s.processingState == ProcessingState.completed) {
          p.pause();
          p.seek(Duration.zero);
        }
      }));
      await p.play();
    } catch (e) {
      if (mounted) toast(context, 'Couldn\'t play this message');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    for (final s in _subs) {
      s.cancel();
    }
    _player?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final media = widget.message.media ?? {};
    final wave = ((media['wave'] as List?) ?? const []).map((e) => (e as num).toDouble()).toList();
    final total = _dur ?? Duration(milliseconds: (media['dur'] as num?)?.toInt() ?? 0);
    final progress = total.inMilliseconds == 0 ? 0.0 : (_pos.inMilliseconds / total.inMilliseconds).clamp(0.0, 1.0);
    return SizedBox(
      width: 230,
      child: Row(children: [
        GestureDetector(
          onTap: _toggle,
          child: Container(
            width: 40,
            height: 40,
            decoration: const BoxDecoration(color: HimeColors.yellow, shape: BoxShape.circle),
            child: _loading
                ? const Padding(padding: EdgeInsets.all(11), child: CircularProgressIndicator(strokeWidth: 2.2, color: HimeColors.ink))
                : Icon(_playing ? Icons.pause_rounded : Icons.play_arrow_rounded, color: HimeColors.ink),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(
              height: 26,
              child: CustomPaint(
                size: Size.infinite,
                painter: _WavePainter(wave, progress, widget.color, context.palette.muted.withValues(alpha: 0.45)),
              ),
            ),
            Text(Fmt.duration(_playing || _pos > Duration.zero ? _pos : total),
                style: context.text.labelSmall?.copyWith(fontSize: 10.5)),
          ]),
        ),
      ]),
    );
  }
}

class _WavePainter extends CustomPainter {
  _WavePainter(this.samples, this.progress, this.active, this.idle);
  final List<double> samples;
  final double progress;
  final Color active;
  final Color idle;

  @override
  void paint(Canvas canvas, Size size) {
    final data = samples.isEmpty ? List<double>.generate(32, (i) => 0.3 + 0.25 * math.sin(i * 0.9).abs()) : samples;
    final n = data.length;
    final gap = 2.0;
    final w = math.max(1.5, (size.width - gap * (n - 1)) / n);
    final paint = Paint()..strokeCap = StrokeCap.round;
    for (var i = 0; i < n; i++) {
      final x = i * (w + gap) + w / 2;
      final h = math.max(3.0, data[i].clamp(0.0, 1.0) * size.height);
      paint
        ..color = (i / n) <= progress ? active : idle
        ..strokeWidth = w;
      canvas.drawLine(Offset(x, (size.height - h) / 2), Offset(x, (size.height + h) / 2), paint);
    }
  }

  @override
  bool shouldRepaint(covariant _WavePainter old) => old.progress != progress || old.samples != samples;
}

class DocumentTile extends StatefulWidget {
  const DocumentTile({super.key, required this.message, required this.core});
  final ChatMessage message;
  final HimeCore core;

  @override
  State<DocumentTile> createState() => _DocumentTileState();
}

class _DocumentTileState extends State<DocumentTile> {
  bool _busy = false;

  Future<void> _open() async {
    setState(() => _busy = true);
    try {
      final f = await widget.core.chats.mediaFile(widget.message);
      if (f != null && mounted) await openLocalFile(context, f, widget.message.media?['name'] as String?);
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final media = widget.message.media ?? {};
    final name = (media['name'] as String?) ?? 'Document';
    final ext = name.contains('.') ? name.split('.').last.toUpperCase() : 'FILE';
    final bar = widget.core.chats.progress[widget.message.id];
    return InkWell(
      onTap: _busy ? null : _open,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        width: 240,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: context.colors.onSurface.withValues(alpha: 0.05), borderRadius: BorderRadius.circular(12)),
        child: Row(children: [
          Container(
            width: 40,
            height: 46,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: HimeColors.yellow, borderRadius: BorderRadius.circular(8)),
            child: Text(ext.length > 4 ? ext.substring(0, 4) : ext,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11, color: HimeColors.ink)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(name, maxLines: 2, overflow: TextOverflow.ellipsis, style: context.text.titleSmall),
              const SizedBox(height: 2),
              Text(Fmt.bytes((media['size'] as num?)?.toInt() ?? 0), style: context.text.labelSmall),
              if ((_busy || widget.message.localState == 1) && bar != null)
                ValueListenableBuilder<double>(
                  valueListenable: bar,
                  builder: (_, v, __) => Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: LinearProgressIndicator(value: v, minHeight: 3, borderRadius: BorderRadius.circular(2)),
                  ),
                ),
            ]),
          ),
          if (_busy) const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
        ]),
      ),
    );
  }
}

class _ContactCard extends StatelessWidget {
  const _ContactCard({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final phones = ((data['phones'] as List?) ?? const []).cast<String>();
    return SizedBox(
      width: 230,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          HimeAvatar(name: '${data['name'] ?? '?'}', size: 40),
          const SizedBox(width: 10),
          Expanded(child: Text('${data['name'] ?? 'Contact'}', style: context.text.titleSmall)),
        ]),
        for (final p in phones.take(3))
          TextButton.icon(
            style: TextButton.styleFrom(padding: EdgeInsets.zero, alignment: Alignment.centerLeft),
            onPressed: () => launchUrl(Uri.parse('tel:${p.replaceAll(' ', '')}')),
            icon: const Icon(Icons.phone_rounded, size: 16),
            label: Text(p),
          ),
      ]),
    );
  }
}

class _LocationCard extends StatelessWidget {
  const _LocationCard({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final lat = (data['lat'] as num?)?.toDouble() ?? 0;
    final lng = (data['lng'] as num?)?.toDouble() ?? 0;
    return InkWell(
      onTap: () => launchUrl(Uri.parse('https://www.google.com/maps/search/?api=1&query=$lat,$lng'), mode: LaunchMode.externalApplication),
      child: Container(
        width: 230,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: context.colors.onSurface.withValues(alpha: 0.05), borderRadius: BorderRadius.circular(12)),
        child: Row(children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: const BoxDecoration(color: HimeColors.yellow, shape: BoxShape.circle),
            child: const Icon(Icons.location_on_rounded, color: HimeColors.ink),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text((data['label'] as String?) ?? 'Shared location', style: context.text.titleSmall),
              Text('${lat.toStringAsFixed(5)}, ${lng.toStringAsFixed(5)}', style: context.text.labelSmall),
              Text('Open in Maps', style: context.text.labelSmall?.copyWith(color: HimeColors.read)),
            ]),
          ),
        ]),
      ),
    );
  }
}

class LinkPreviewCard extends StatelessWidget {
  const LinkPreviewCard({super.key, required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final url = '${data['url'] ?? ''}';
    return InkWell(
      onTap: () => launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication),
      child: Container(
        width: 250,
        margin: const EdgeInsets.only(bottom: 4),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: context.colors.onSurface.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(10),
          border: const Border(left: BorderSide(color: HimeColors.yellowDeep, width: 3)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (data['site'] != null) Text('${data['site']}', style: context.text.labelSmall),
          if (data['title'] != null)
            Text('${data['title']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: context.text.titleSmall),
          if (data['desc'] != null)
            Text('${data['desc']}', maxLines: 3, overflow: TextOverflow.ellipsis, style: context.text.bodySmall),
        ]),
      ),
    );
  }
}

/// Fetches Open Graph metadata on the sender's phone; the result travels
/// inside the encrypted message, so recipients never contact the website.
class LinkPreviewFetcher {
  static final _cache = <String, Map<String, dynamic>?>{};

  static Future<Map<String, dynamic>?> fetch(String rawUrl) async {
    final url = rawUrl.startsWith('http') ? rawUrl : 'https://$rawUrl';
    if (_cache.containsKey(url)) return _cache[url];
    try {
      final res = await http
          .get(Uri.parse(url), headers: {'User-Agent': 'HimeLinkPreview/1.0', 'Accept': 'text/html'})
          .timeout(const Duration(seconds: 5));
      if (res.statusCode >= 400 || !(res.headers['content-type'] ?? '').contains('html')) return _cache[url] = null;
      final html = res.body.length > 200000 ? res.body.substring(0, 200000) : res.body;
      String? meta(String prop) {
        final r = RegExp('<meta[^>]+(?:property|name)=["\']$prop["\'][^>]*content=["\']([^"\']*)["\']', caseSensitive: false);
        final r2 = RegExp('<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']$prop["\']', caseSensitive: false);
        return r.firstMatch(html)?.group(1) ?? r2.firstMatch(html)?.group(1);
      }

      final title = meta('og:title') ?? RegExp(r'<title[^>]*>([^<]*)</title>', caseSensitive: false).firstMatch(html)?.group(1);
      if (title == null || title.trim().isEmpty) return _cache[url] = null;
      final desc = meta('og:description') ?? meta('description');
      return _cache[url] = {
        'url': url,
        'title': _unescape(title.trim()),
        if (desc != null) 'desc': _unescape(desc),
        'site': meta('og:site_name') ?? Uri.parse(url).host,
      };
    } catch (_) {
      return _cache[url] = null;
    }
  }

  static String _unescape(String s) => s
      .replaceAll('&amp;', '&')
      .replaceAll('&quot;', '"')
      .replaceAll('&#39;', "'")
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>');
}

/// Compact emoji keyboard (no native dependency).
class EmojiPanel extends StatelessWidget {
  const EmojiPanel({super.key, required this.onPick});
  final ValueChanged<String> onPick;

  static const groups = {
    'Smileys': '😀😃😄😁😆😅🤣😂🙂🙃😉😊😇🥰😍🤩😘😗😚😙😋😛😜🤪😝🤑🤗🤭🤫🤔🤐🤨😐😑😶😏😒🙄😬😮‍💨🤥😌😔😪🤤😴😷🤒🤕🤢🤮🥵🥶🥴😵🤯🤠🥳😎🤓🧐😕😟🙁😮😯😲😳🥺😦😧😨😰😥😢😭😱😖😣😞😓😩😫🥱😤😡😠🤬',
    'Gestures': '👋🤚🖐️✋🖖👌🤌🤏✌️🤞🤟🤘🤙👈👉👆🖕👇☝️👍👎✊👊🤛🤜👏🙌👐🤲🤝🙏✍️💅🤳💪🦾🙇🙋🙆🙅🤷🤦',
    'Hearts': '❤️🧡💛💚💙💜🖤🤍🤎💔❣️💕💞💓💗💖💘💝💟♥️🔥✨⭐🌟💫💥💯✅❌⚡🎉🎊🎁🏆🥇',
    'Nature': '🌸🌺🌻🌼🌷🌹🍀🌿🌱🌴🌵🍁🍂🌈☀️🌤️⛅🌧️⛈️❄️☃️🌊🐶🐱🐭🐹🐰🦊🐻🐼🐨🐯🦁🐮🐷🐸🐵🐔🐧🐦🦋🐝🐞🦚🦜',
    'Food': '🍎🍊🍋🍌🍉🍇🍓🫐🍒🥭🍍🥥🥝🍅🥑🌽🥕🍞🧀🍳🥞🍔🍟🍕🌭🥪🌮🍜🍛🍚🍙🍘🍥🥟🍩🍪🎂🍰🧁🍫🍬🍭☕🍵🧃🥤🧋',
    'Activities': '⚽🏀🏈⚾🎾🏐🏉🎱🏓🏸🏏🏑🥅⛳🏹🎣🥊🥋🎽🛹⛸️🎿🏂🏋️🤸🧘🎮🎲🧩🎯🎳🎨🎬🎤🎧🎼🎹🥁🎷🎺🎸',
    'Travel': '🚗🚕🚙🚌🏎️🚓🚑🚒🛺🚲🛵🏍️✈️🚀🛸🚁⛵🚤🛳️🚂🚆🚇🗺️🏔️🏕️🏖️🏝️🏛️🕌🛕⛪🗼🗽🏠🏡🏢🏥🏦🏨🏫',
    'Objects': '📱💻⌨️🖥️🖨️📷📸📹🎥📞☎️📺📻⏰⌛💡🔦🕯️💰💳💎🔧🔨🧰🔑🗝️🔒🔓📦📫✉️📝📚📖🔖📎✂️📌📍',
  };

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: groups.length,
      child: SizedBox(
        height: 280,
        child: Column(children: [
          TabBar(
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            labelColor: context.colors.onSurface,
            indicatorColor: HimeColors.yellowDeep,
            tabs: [for (final k in groups.keys) Tab(text: k)],
          ),
          Expanded(
            child: TabBarView(children: [
              for (final g in groups.values)
                GridView.count(
                  crossAxisCount: 8,
                  padding: const EdgeInsets.all(6),
                  children: [
                    for (final e in g.characters)
                      InkWell(
                        borderRadius: BorderRadius.circular(8),
                        onTap: () => onPick(e),
                        child: Center(child: Text(e, style: const TextStyle(fontSize: 26))),
                      ),
                  ],
                ),
            ]),
          ),
        ]),
      ),
    );
  }
}
