import 'dart:async';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'theme.dart';
import 'utils.dart';

/// Hime brand mark (speech bubble with an "h" and a spark) plus wordmark.
class HimeLogo extends StatelessWidget {
  const HimeLogo({super.key, this.size = 40, this.showWordmark = true, this.tagline = false});
  final double size;
  final bool showWordmark;
  final bool tagline;

  @override
  Widget build(BuildContext context) {
    final mark = Image.asset('assets/images/hime_mark.png', width: size, height: size, filterQuality: FilterQuality.medium);
    if (!showWordmark) return mark;
    return Row(mainAxisSize: MainAxisSize.min, children: [
      mark,
      SizedBox(width: size * 0.22),
      Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text('hime',
            style: TextStyle(
              fontFamily: 'Poppins',
              fontWeight: FontWeight.w700,
              fontSize: size * 0.62,
              height: 1.0,
              letterSpacing: -0.5,
              color: context.colors.onSurface,
            )),
        if (tagline)
          Text('Connect Without Limits.', style: context.text.labelSmall?.copyWith(letterSpacing: 0.2)),
      ]),
    ]);
  }
}

/// Subtle press-down scale used on tappable cards and buttons.
class Pressable extends StatefulWidget {
  const Pressable({super.key, required this.child, this.onTap, this.onLongPress, this.scale = 0.97});
  final Widget child;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final double scale;

  @override
  State<Pressable> createState() => _PressableState();
}

class _PressableState extends State<Pressable> {
  bool _down = false;

  void _set(bool v) {
    if (_down != v) setState(() => _down = v);
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: widget.onTap == null ? null : (_) => _set(true),
      onTapCancel: () => _set(false),
      onTapUp: (_) => _set(false),
      onTap: widget.onTap,
      onLongPress: widget.onLongPress,
      child: AnimatedScale(
        scale: _down ? widget.scale : 1,
        duration: const Duration(milliseconds: 110),
        curve: Curves.easeOut,
        child: widget.child,
      ),
    );
  }
}

/// Primary call to action with a built-in loading state.
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({super.key, required this.label, this.onPressed, this.loading = false, this.icon});
  final String label;
  final VoidCallback? onPressed;
  final bool loading;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: loading ? null : onPressed,
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 180),
        child: loading
            ? const SizedBox(
                key: ValueKey('l'),
                width: 22,
                height: 22,
                child: CircularProgressIndicator(strokeWidth: 2.4, color: HimeColors.ink),
              )
            : Row(key: const ValueKey('t'), mainAxisSize: MainAxisSize.min, children: [
                if (icon != null) ...[Icon(icon, size: 20), const SizedBox(width: 8)],
                Text(label),
              ]),
      ),
    );
  }
}

/// Text input with consistent styling and an optional password toggle.
class HimeField extends StatefulWidget {
  const HimeField({
    super.key,
    this.controller,
    this.label,
    this.hint,
    this.validator,
    this.keyboardType,
    this.obscure = false,
    this.prefix,
    this.suffix,
    this.maxLength,
    this.maxLines = 1,
    this.textInputAction,
    this.onSubmitted,
    this.autofillHints,
    this.autofocus = false,
    this.onChanged,
    this.textCapitalization = TextCapitalization.none,
    this.inputFormatters,
    this.enabled = true,
  });

  final TextEditingController? controller;
  final String? label;
  final String? hint;
  final String? Function(String?)? validator;
  final TextInputType? keyboardType;
  final bool obscure;
  final Widget? prefix;
  final Widget? suffix;
  final int? maxLength;
  final int maxLines;
  final TextInputAction? textInputAction;
  final ValueChanged<String>? onSubmitted;
  final Iterable<String>? autofillHints;
  final bool autofocus;
  final ValueChanged<String>? onChanged;
  final TextCapitalization textCapitalization;
  final List<TextInputFormatter>? inputFormatters;
  final bool enabled;

  @override
  State<HimeField> createState() => _HimeFieldState();
}

class _HimeFieldState extends State<HimeField> {
  late bool _hidden = widget.obscure;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: widget.controller,
      validator: widget.validator,
      keyboardType: widget.keyboardType,
      obscureText: _hidden,
      maxLength: widget.maxLength,
      maxLines: widget.obscure ? 1 : widget.maxLines,
      minLines: 1,
      enabled: widget.enabled,
      textInputAction: widget.textInputAction,
      onFieldSubmitted: widget.onSubmitted,
      autofillHints: widget.autofillHints,
      autofocus: widget.autofocus,
      onChanged: widget.onChanged,
      textCapitalization: widget.textCapitalization,
      inputFormatters: widget.inputFormatters,
      decoration: InputDecoration(
        labelText: widget.label,
        hintText: widget.hint,
        prefixIcon: widget.prefix,
        counterText: '',
        suffixIcon: widget.obscure
            ? IconButton(
                tooltip: _hidden ? 'Show password' : 'Hide password',
                icon: Icon(_hidden ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                onPressed: () => setState(() => _hidden = !_hidden),
              )
            : widget.suffix,
      ),
    );
  }
}

/// Caches short-lived signed URLs for private images (avatars, statuses).
class SignedUrls {
  static final _cache = <String, (String, DateTime)>{};
  static final _inflight = <String, Future<String?>>{};

  static Future<String?> get(String bucket, String path, {int ttlSeconds = 3600}) {
    final key = '$bucket/$path';
    final hit = _cache[key];
    if (hit != null && hit.$2.isAfter(DateTime.now())) return Future.value(hit.$1);
    return _inflight[key] ??= () async {
      try {
        final url = await Supabase.instance.client.storage.from(bucket).createSignedUrl(path, ttlSeconds);
        _cache[key] = (url, DateTime.now().add(Duration(seconds: ttlSeconds - 120)));
        return url;
      } catch (_) {
        return null;
      } finally {
        _inflight.remove(key);
      }
    }();
  }

  static void clear() => _cache.clear();
}

/// Profile / group picture with initials fallback and online indicator.
class HimeAvatar extends StatelessWidget {
  const HimeAvatar({
    super.key,
    required this.name,
    this.path,
    this.version = 0,
    this.size = 48,
    this.online = false,
    this.icon,
    this.bucket = 'avatars',
  });

  final String name;
  final String? path;
  final int version;
  final double size;
  final bool online;
  final IconData? icon;
  final String bucket;

  static const _tints = [
    Color(0xFFFFE9A8), Color(0xFFD9F2E6), Color(0xFFDCE8FF), Color(0xFFFFDDE4),
    Color(0xFFEADFFF), Color(0xFFFFE3CC), Color(0xFFD7F3F7),
  ];

  @override
  Widget build(BuildContext context) {
    final tint = _tints[name.hashCode.abs() % _tints.length];
    final fallback = Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: context.isDark ? tint.withValues(alpha: 0.25) : tint, shape: BoxShape.circle),
      child: icon != null
          ? Icon(icon, size: size * 0.48, color: context.colors.onSurface.withValues(alpha: 0.75))
          : Text(Fmt.initials(name),
              style: TextStyle(
                fontFamily: 'Poppins',
                fontWeight: FontWeight.w600,
                fontSize: size * 0.36,
                color: context.colors.onSurface.withValues(alpha: 0.8),
              )),
    );
    Widget child = fallback;
    if (path != null && path!.isNotEmpty) {
      child = FutureBuilder<String?>(
        future: SignedUrls.get(bucket, path!),
        builder: (context, snap) {
          final url = snap.data;
          if (url == null) return fallback;
          final px = (size * MediaQuery.devicePixelRatioOf(context)).round();
          return ClipOval(
            child: CachedNetworkImage(
              imageUrl: url,
              cacheKey: '$bucket/$path?v=$version',
              width: size,
              height: size,
              fit: BoxFit.cover,
              memCacheWidth: px,
              fadeInDuration: const Duration(milliseconds: 150),
              placeholder: (_, __) => fallback,
              errorWidget: (_, __, ___) => fallback,
            ),
          );
        },
      );
    }
    return SizedBox(
      width: size,
      height: size,
      child: Stack(clipBehavior: Clip.none, children: [
        Positioned.fill(child: child),
        if (online)
          Positioned(
            right: -1,
            bottom: -1,
            child: Container(
              width: size * 0.28,
              height: size * 0.28,
              decoration: BoxDecoration(
                color: HimeColors.online,
                shape: BoxShape.circle,
                border: Border.all(color: Theme.of(context).scaffoldBackgroundColor, width: 2),
              ),
            ),
          ),
      ]),
    );
  }
}

/// Lightweight shimmer used for loading skeletons (one controller per list).
class Shimmer extends StatefulWidget {
  const Shimmer({super.key, required this.child});
  final Widget child;

  @override
  State<Shimmer> createState() => _ShimmerState();
}

class _ShimmerState extends State<Shimmer> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1300))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final base = context.palette.skeleton;
    final hi = context.isDark ? const Color(0xFF3A3B40) : const Color(0xFFF7F7F7);
    return AnimatedBuilder(
      animation: _c,
      child: widget.child,
      builder: (context, child) => ShaderMask(
        blendMode: BlendMode.srcATop,
        shaderCallback: (rect) => LinearGradient(
          colors: [base, hi, base],
          stops: const [0.35, 0.5, 0.65],
          begin: Alignment(-1.6 + 3.2 * _c.value, 0),
          end: Alignment(-0.6 + 3.2 * _c.value, 0),
        ).createShader(rect),
        child: child,
      ),
    );
  }
}

class SkeletonBox extends StatelessWidget {
  const SkeletonBox({super.key, this.width, this.height = 12, this.radius = 8, this.circle = false});
  final double? width;
  final double height;
  final double radius;
  final bool circle;

  @override
  Widget build(BuildContext context) => Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: context.palette.skeleton,
          shape: circle ? BoxShape.circle : BoxShape.rectangle,
          borderRadius: circle ? null : BorderRadius.circular(radius),
        ),
      );
}

/// Skeleton for list screens (chats, calls, contacts).
class ListSkeleton extends StatelessWidget {
  const ListSkeleton({super.key, this.count = 8});
  final int count;

  @override
  Widget build(BuildContext context) {
    return Shimmer(
      child: ListView.builder(
        physics: const NeverScrollableScrollPhysics(),
        itemCount: count,
        itemBuilder: (_, i) => Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Row(children: [
            const SkeletonBox(width: 52, height: 52, circle: true),
            const SizedBox(width: 14),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SkeletonBox(width: 120.0 + (i % 3) * 30, height: 13),
                const SizedBox(height: 9),
                SkeletonBox(width: 180.0 + (i % 2) * 40, height: 11),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.title, this.message, this.action});
  final IconData icon;
  final String title;
  final String? message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(
            width: 88,
            height: 88,
            decoration: BoxDecoration(color: context.colors.primaryContainer, shape: BoxShape.circle),
            child: Icon(icon, size: 40, color: context.isDark ? HimeColors.yellow : HimeColors.ink),
          ),
          const SizedBox(height: 20),
          Text(title, textAlign: TextAlign.center, style: context.text.titleLarge),
          if (message != null) ...[
            const SizedBox(height: 8),
            Text(message!, textAlign: TextAlign.center, style: context.text.bodyMedium?.copyWith(color: context.palette.muted)),
          ],
          if (action != null) ...[const SizedBox(height: 20), action!],
        ]),
      ),
    );
  }
}

class ErrorState extends StatelessWidget {
  const ErrorState({super.key, required this.error, this.onRetry});
  final Object error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => EmptyState(
        icon: Icons.cloud_off_rounded,
        title: 'Couldn\'t load this',
        message: friendlyError(error),
        action: onRetry == null
            ? null
            : OutlinedButton.icon(
                style: OutlinedButton.styleFrom(minimumSize: const Size(140, 44)),
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Try again'),
              ),
      );
}

class CenteredLoader extends StatelessWidget {
  const CenteredLoader({super.key});
  @override
  Widget build(BuildContext context) => const Center(child: CircularProgressIndicator(strokeWidth: 2.6));
}

class UnreadBadge extends StatelessWidget {
  const UnreadBadge({super.key, required this.count, this.muted = false});
  final int count;
  final bool muted;

  @override
  Widget build(BuildContext context) {
    return AnimatedScale(
      scale: count > 0 ? 1 : 0,
      duration: const Duration(milliseconds: 180),
      child: Container(
        constraints: const BoxConstraints(minWidth: 22),
        height: 22,
        padding: const EdgeInsets.symmetric(horizontal: 6),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: muted ? context.palette.muted.withValues(alpha: 0.35) : HimeColors.yellow,
          borderRadius: BorderRadius.circular(11),
        ),
        child: Text(count > 99 ? '99+' : '$count',
            style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: HimeColors.ink)),
      ),
    );
  }
}

/// Three bouncing dots for "typing…".
class TypingDots extends StatefulWidget {
  const TypingDots({super.key, this.color, this.size = 6});
  final Color? color;
  final double size;

  @override
  State<TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<TypingDots> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 900))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.color ?? HimeColors.yellowDeep;
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) => Row(mainAxisSize: MainAxisSize.min, children: List.generate(3, (i) {
        final t = ((_c.value - i * 0.18) % 1.0);
        final lift = t < 0.4 ? (t < 0.2 ? t / 0.2 : (0.4 - t) / 0.2) : 0.0;
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 1.5),
          transform: Matrix4.translationValues(0, -3 * lift, 0),
          width: widget.size,
          height: widget.size,
          decoration: BoxDecoration(color: color.withValues(alpha: 0.5 + 0.5 * lift), shape: BoxShape.circle),
        );
      })),
    );
  }
}

/// Settings-style grouped list.
class SettingsGroup extends StatelessWidget {
  const SettingsGroup({super.key, this.title, required this.children});
  final String? title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (title != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(4, 8, 4, 8),
            child: Text(title!.toUpperCase(), style: context.text.labelSmall?.copyWith(letterSpacing: 0.8)),
          ),
        Container(
          decoration: BoxDecoration(
            color: context.colors.surface,
            borderRadius: BorderRadius.circular(HimeRadius.lg),
            border: Border.all(color: context.palette.border),
          ),
          clipBehavior: Clip.antiAlias,
          child: Column(children: [
            for (var i = 0; i < children.length; i++) ...[
              children[i],
              if (i != children.length - 1) Divider(indent: 56, height: 1, color: context.palette.border),
            ],
          ]),
        ),
      ]),
    );
  }
}

class SettingsTile extends StatelessWidget {
  const SettingsTile({super.key, required this.icon, required this.title, this.subtitle, this.onTap, this.trailing, this.danger = false});
  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback? onTap;
  final Widget? trailing;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final color = danger ? context.colors.error : context.colors.onSurface;
    return ListTile(
      onTap: onTap,
      leading: Icon(icon, color: color),
      title: Text(title, style: context.text.titleSmall?.copyWith(color: color, fontSize: 15)),
      subtitle: subtitle == null ? null : Text(subtitle!, maxLines: 2, overflow: TextOverflow.ellipsis),
      trailing: trailing ?? (onTap == null ? null : Icon(Icons.chevron_right_rounded, color: context.palette.muted)),
    );
  }
}

class SheetAction {
  const SheetAction(this.icon, this.label, this.onTap, {this.danger = false});
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool danger;
}

Future<void> showActionSheet(BuildContext context, {String? title, required List<SheetAction> actions}) {
  return showModalBottomSheet<void>(
    context: context,
    builder: (ctx) => SafeArea(
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (title != null)
          Padding(padding: const EdgeInsets.fromLTRB(24, 0, 24, 8), child: Text(title, style: ctx.text.titleMedium)),
        for (final a in actions)
          ListTile(
            leading: Icon(a.icon, color: a.danger ? ctx.colors.error : null),
            title: Text(a.label, style: TextStyle(color: a.danger ? ctx.colors.error : null)),
            onTap: () {
              Navigator.of(ctx).pop();
              a.onTap();
            },
          ),
        const SizedBox(height: 8),
      ]),
    ),
  );
}

Future<bool> confirm(BuildContext context,
    {required String title, String? message, String confirmLabel = 'OK', bool danger = false}) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: message == null ? null : Text(message),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
        TextButton(
          onPressed: () => Navigator.pop(ctx, true),
          style: danger ? TextButton.styleFrom(foregroundColor: ctx.colors.error) : null,
          child: Text(confirmLabel),
        ),
      ],
    ),
  );
  return ok ?? false;
}

Future<String?> promptText(BuildContext context,
    {required String title, String? initial, String? hint, int maxLength = 140, int maxLines = 1}) {
  final c = TextEditingController(text: initial);
  return showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: c,
        autofocus: true,
        maxLength: maxLength,
        maxLines: maxLines,
        minLines: 1,
        decoration: InputDecoration(hintText: hint),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
        TextButton(onPressed: () => Navigator.pop(ctx, c.text.trim()), child: const Text('Save')),
      ],
    ),
  );
}

void toast(BuildContext context, String message) {
  final m = ScaffoldMessenger.maybeOf(context);
  m?.hideCurrentSnackBar();
  m?.showSnackBar(SnackBar(content: Text(message), duration: const Duration(seconds: 3)));
}

/// Runs an async action with a toast on failure; returns success.
Future<bool> guard(BuildContext context, Future<void> Function() action, {String? success}) async {
  try {
    await action();
    if (success != null && context.mounted) toast(context, success);
    return true;
  } catch (e) {
    if (context.mounted) toast(context, friendlyError(e));
    return false;
  }
}

/// Banner shown at the top of screens while offline or reconnecting.
class ConnectionBanner extends StatelessWidget {
  const ConnectionBanner({super.key, required this.online});
  final bool online;

  @override
  Widget build(BuildContext context) {
    return AnimatedSize(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOut,
      child: online
          ? const SizedBox(width: double.infinity)
          : Container(
              width: double.infinity,
              color: context.colors.primaryContainer,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
              child: Row(children: [
                const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
                const SizedBox(width: 10),
                Text('Waiting for network…', style: context.text.labelMedium?.copyWith(color: context.colors.onSurface)),
              ]),
            ),
    );
  }
}

/// Debounced, cancellable stream subscription bag for controllers.
class Subscriptions {
  final _subs = <StreamSubscription<dynamic>>[];
  void add(StreamSubscription<dynamic> s) => _subs.add(s);
  Future<void> cancel() async {
    for (final s in _subs) {
      await s.cancel();
    }
    _subs.clear();
  }
}
