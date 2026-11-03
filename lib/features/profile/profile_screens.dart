import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/config.dart';
import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import '../../services/session.dart';
import '../chats/extra_screens.dart';
import '../chats/models.dart';
import '../contacts/contacts.dart';

String profileLink(String userId) {
  final base = AppConfig.instance.inviteBaseUrl;
  final root = base.endsWith('/join') ? base.substring(0, base.length - 5) : base;
  return '$root/user/$userId';
}

class UserProfileScreen extends ConsumerStatefulWidget {
  const UserProfileScreen({super.key, required this.userId});
  final String userId;

  @override
  ConsumerState<UserProfileScreen> createState() => _UserProfileScreenState();
}

class _UserProfileScreenState extends ConsumerState<UserProfileScreen> {
  late final HimeCore core = ref.read(coreProvider);
  late final repo = ContactsRepo(core);
  Profile? profile;
  bool loading = true;
  ValueNotifier<PresenceInfo>? presence;

  @override
  void initState() {
    super.initState();
    if (widget.userId == core.userId) {
      WidgetsBinding.instance.addPostFrameCallback((_) => context.pushReplacement('/profile/edit'));
      return;
    }
    presence = core.presence.watch(widget.userId);
    _load();
  }

  @override
  void dispose() {
    if (presence != null) core.presence.unwatch(widget.userId);
    super.dispose();
  }

  Future<void> _load() async {
    try {
      profile = await core.profiles.fetch(widget.userId);
    } catch (_) {}
    if (mounted) setState(() => loading = false);
  }

  Future<void> _call(bool video) async {
    final p = profile;
    if (p == null) return;
    try {
      final conv = await core.sb.rpc('get_or_create_direct', params: {'p_other': p.id}) as String;
      await core.calls.startCall(conversationId: conv, peerId: p.id, peerName: p.name, video: video);
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = profile;
    return Scaffold(
      appBar: AppBar(),
      body: loading
          ? const CenteredLoader()
          : p == null
              ? const EmptyState(icon: Icons.person_off_outlined, title: 'Profile unavailable', message: 'This account may have been deleted.')
              : ListView(padding: const EdgeInsets.only(bottom: 32), children: [
                  const SizedBox(height: 8),
                  Center(child: HimeAvatar(name: p.name, path: p.avatarPath, version: p.avatarVersion, size: 120)),
                  const SizedBox(height: 14),
                  Text(p.name, textAlign: TextAlign.center, style: context.text.headlineSmall),
                  if (p.username != null)
                    Text('@${p.username}', textAlign: TextAlign.center, style: context.text.bodyMedium?.copyWith(color: context.palette.muted)),
                  if (presence != null)
                    ValueListenableBuilder<PresenceInfo>(
                      valueListenable: presence!,
                      builder: (_, info, __) {
                        final text = info.online ? 'online' : (info.lastSeen == null ? '' : Fmt.lastSeen(info.lastSeen));
                        if (text.isEmpty) return const SizedBox.shrink();
                        return Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(text,
                              textAlign: TextAlign.center,
                              style: context.text.labelMedium?.copyWith(color: info.online ? HimeColors.online : context.palette.muted)),
                        );
                      },
                    ),
                  const SizedBox(height: 18),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Row(children: [
                      _ProfileAction(icon: Icons.chat_bubble_outline_rounded, label: 'Message', onTap: () => openDirectChat(context, core, p.id)),
                      _ProfileAction(icon: Icons.call_outlined, label: 'Voice', onTap: p.blockedByMe ? null : () => _call(false)),
                      _ProfileAction(icon: Icons.videocam_outlined, label: 'Video', onTap: p.blockedByMe ? null : () => _call(true)),
                    ]),
                  ),
                  if ((p.about ?? '').isNotEmpty)
                    SettingsGroup(title: 'About', children: [ListTile(title: Text(p.about!))]),
                  SettingsGroup(children: [
                    SettingsTile(
                      icon: p.isContact ? Icons.person_remove_outlined : Icons.person_add_alt_outlined,
                      title: p.isContact ? 'Remove from contacts' : 'Add to contacts',
                      onTap: () async {
                        await guard(context, () => p.isContact ? repo.remove(p.id) : repo.add(p.id),
                            success: p.isContact ? 'Removed from contacts' : 'Added to contacts');
                        await _load();
                      },
                    ),
                    SettingsTile(
                      icon: Icons.share_outlined,
                      title: 'Share profile',
                      onTap: () => SharePlus.instance.share(ShareParams(text: 'Chat with ${p.name} on Hime: ${profileLink(p.id)}')),
                    ),
                  ]),
                  SettingsGroup(children: [
                    SettingsTile(
                      icon: Icons.block_rounded,
                      title: p.blockedByMe ? 'Unblock ${p.name}' : 'Block ${p.name}',
                      danger: !p.blockedByMe,
                      onTap: () async {
                        await toggleBlock(context, core, p.id, p.blockedByMe);
                        unawaited(core.chatList.refresh());
                        await _load();
                      },
                    ),
                    SettingsTile(
                      icon: Icons.thumb_down_alt_outlined,
                      title: 'Report ${p.name}',
                      danger: true,
                      onTap: () => showReportSheet(context, core, userId: p.id),
                    ),
                  ]),
                ]),
    );
  }
}

class _ProfileAction extends StatelessWidget {
  const _ProfileAction({required this.icon, required this.label, this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Expanded(
        child: Pressable(
          onTap: onTap,
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 6),
            padding: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: context.colors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: context.palette.border),
            ),
            child: Column(children: [
              Icon(icon, color: onTap == null ? context.palette.muted : HimeColors.yellowDeep),
              const SizedBox(height: 6),
              Text(label, style: context.text.labelMedium),
            ]),
          ),
        ),
      );
}

class EditProfileScreen extends ConsumerStatefulWidget {
  const EditProfileScreen({super.key});

  @override
  ConsumerState<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends ConsumerState<EditProfileScreen> {
  bool uploading = false;

  Future<void> _update(Map<String, dynamic> values) async {
    final session = ref.read(sessionProvider);
    final core = ref.read(coreProvider);
    await core.sb.from('profiles').update(values).eq('id', core.userId);
    await session.refreshProfile();
  }

  Future<void> _changePhoto() async {
    final core = ref.read(coreProvider);
    final me = ref.read(sessionProvider).profile;
    await showActionSheet(context, title: 'Profile photo', actions: [
      SheetAction(Icons.photo_library_outlined, 'Choose photo', () async {
        setState(() => uploading = true);
        await guard(context, () async {
          final path = await uploadAvatar(core, 'users/${core.userId}');
          if (path == null) return;
          await _update({'avatar_path': path, 'avatar_version': (me?.avatarVersion ?? 0) + 1});
        });
        if (mounted) setState(() => uploading = false);
      }),
      if (me?.avatarPath != null)
        SheetAction(Icons.hide_image_outlined, 'Remove photo', () async {
          await guard(context, () => _update({'avatar_path': null, 'avatar_version': (me?.avatarVersion ?? 0) + 1}));
        }, danger: true),
    ]);
  }

  Future<void> _editName(MyProfile me) async {
    final v = await promptText(context, title: 'Your name', initial: me.displayName, maxLength: 64);
    if (v == null || v.isEmpty || !mounted) return;
    await guard(context, () => _update({'display_name': v}));
  }

  Future<void> _editAbout(MyProfile me) async {
    final v = await promptText(context, title: 'About', initial: me.about, maxLength: 140, maxLines: 3);
    if (v == null || !mounted) return;
    await guard(context, () => _update({'about': v}));
  }

  Future<void> _editUsername(MyProfile me) async {
    final core = ref.read(coreProvider);
    final v = await promptText(context, title: 'Username', initial: me.username, hint: 'letters, numbers, _ and .', maxLength: 24);
    if (v == null || !mounted) return;
    final name = v.trim().toLowerCase().replaceAll('@', '');
    if (name == me.username) return;
    final invalid = Validators.username(name);
    if (invalid != null) {
      toast(context, invalid);
      return;
    }
    await guard(context, () async {
      final free = await core.sb.rpc('is_username_available', params: {'p_username': name}) as bool;
      if (!free) throw StateError('That username is taken.');
      await _update({'username': name});
    }, success: 'Username updated');
  }

  void _showQr(MyProfile me) {
    final link = profileLink(me.id);
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('My QR code'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(
            color: Colors.white,
            padding: const EdgeInsets.all(12),
            child: QrImageView(data: link, size: 220),
          ),
          const SizedBox(height: 12),
          Text('People can scan this with their camera to open your Hime profile.', textAlign: TextAlign.center, style: ctx.text.bodySmall),
        ]),
        actions: [
          TextButton(onPressed: () => Clipboard.setData(ClipboardData(text: link)), child: const Text('Copy link')),
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Done')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final me = session.profile;
    final user = session.user;
    if (me == null) return const Scaffold(body: CenteredLoader());
    return Scaffold(
      appBar: AppBar(title: const Text('Profile'), actions: [
        IconButton(tooltip: 'My QR code', icon: const Icon(Icons.qr_code_rounded), onPressed: () => _showQr(me)),
      ]),
      body: ListView(children: [
        const SizedBox(height: 20),
        Center(
          child: Stack(children: [
            HimeAvatar(name: me.name, path: me.avatarPath, version: me.avatarVersion, size: 132),
            Positioned(
              right: 4,
              bottom: 4,
              child: Pressable(
                onTap: uploading ? null : _changePhoto,
                child: Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: HimeColors.yellow,
                    shape: BoxShape.circle,
                    border: Border.all(color: context.colors.surface, width: 3),
                  ),
                  child: uploading
                      ? const Padding(padding: EdgeInsets.all(10), child: CircularProgressIndicator(strokeWidth: 2, color: HimeColors.ink))
                      : const Icon(Icons.photo_camera_rounded, color: HimeColors.ink, size: 20),
                ),
              ),
            ),
          ]),
        ),
        const SizedBox(height: 20),
        SettingsGroup(children: [
          SettingsTile(icon: Icons.person_outline_rounded, title: 'Name', subtitle: me.displayName.isEmpty ? 'Add your name' : me.displayName, onTap: () => _editName(me)),
          SettingsTile(icon: Icons.alternate_email_rounded, title: 'Username', subtitle: me.username == null ? 'Choose a username' : '@${me.username}', onTap: () => _editUsername(me)),
          SettingsTile(icon: Icons.info_outline_rounded, title: 'About', subtitle: me.about.isEmpty ? 'Add a few words about yourself' : me.about, onTap: () => _editAbout(me)),
        ]),
        SettingsGroup(title: 'Sign-in', children: [
          if ((user?.email ?? '').isNotEmpty) SettingsTile(icon: Icons.mail_outline_rounded, title: 'Email', subtitle: user!.email),
          if ((user?.phone ?? '').isNotEmpty) SettingsTile(icon: Icons.phone_outlined, title: 'Phone', subtitle: '+${user!.phone}'),
        ]),
        Padding(
          padding: const EdgeInsets.all(20),
          child: Text(
            'Your name, photo and about are visible to people based on your privacy settings. Your phone number and email are never shown to others.',
            style: context.text.bodySmall?.copyWith(color: context.palette.muted),
          ),
        ),
      ]),
    );
  }
}
