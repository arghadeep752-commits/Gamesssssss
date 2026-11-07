import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:share_plus/share_plus.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show FileOptions;
import 'package:video_player/video_player.dart';

import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import '../../services/e2ee.dart';
import '../../services/session.dart';
import '../contacts/contacts.dart';
import 'chat_list_screen.dart';
import 'message_widgets.dart';
import 'models.dart';

// ---------------------------------------------------------------- args

class ForwardArgs {
  const ForwardArgs(this.messages);
  final List<ChatMessage> messages;
}

class MessageInfoArgs {
  const MessageInfoArgs(this.message, this.summary);
  final ChatMessage message;
  final ChatSummary? summary;
}

class MediaViewerArgs {
  const MediaViewerArgs({required this.file, this.isVideo = false, this.heroTag, this.caption});
  final File file;
  final bool isVideo;
  final String? heroTag;
  final String? caption;
}

// ---------------------------------------------------------------- shared helpers

/// Hands a decrypted local file to another app via the system share sheet
/// (Android does not allow opening raw file:// paths in other apps).
Future<void> openLocalFile(BuildContext context, File file, String? name) async {
  try {
    await SharePlus.instance.share(ShareParams(files: [XFile(file.path, name: name)], subject: name));
  } catch (e) {
    if (context.mounted) toast(context, friendlyError(e));
  }
}

Future<void> toggleBlock(BuildContext context, HimeCore core, String userId, bool currentlyBlocked) async {
  final name = core.profiles.nameOf(userId, fallback: 'this person');
  if (!currentlyBlocked) {
    final ok = await confirm(context,
        title: 'Block $name?',
        message: 'Blocked contacts can\'t call you or send you messages, and won\'t see your last seen, profile photo or status updates.',
        confirmLabel: 'Block',
        danger: true);
    if (!ok || !context.mounted) return;
    await guard(context, () => core.sb.from('user_blocks').insert({'blocker_id': core.userId, 'blocked_id': userId}), success: '$name blocked');
  } else {
    await guard(context, () => core.sb.from('user_blocks').delete().eq('blocker_id', core.userId).eq('blocked_id', userId),
        success: '$name unblocked');
  }
}

/// Reports a person or group. Message content is only attached when the
/// reporter explicitly chooses to include their latest messages.
Future<void> showReportSheet(BuildContext context, HimeCore core,
    {String? userId, String? conversationId, List<ChatMessage> recent = const []}) async {
  const reasons = {
    'spam': 'Spam',
    'harassment': 'Harassment or bullying',
    'inappropriate': 'Inappropriate content',
    'impersonation': 'Impersonation',
    'scam': 'Scam or fraud',
    'other': 'Something else',
  };
  var reason = 'spam';
  var includeMessages = recent.isNotEmpty;
  var block = userId != null;
  final details = TextEditingController();
  final sent = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setSheet) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Report', style: ctx.text.titleLarge),
              const SizedBox(height: 4),
              Text('Reports go to the Hime safety team. The person isn\'t told who reported them.',
                  style: ctx.text.bodySmall?.copyWith(color: ctx.palette.muted)),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 4, children: [
                for (final e in reasons.entries)
                  ChoiceChip(
                    label: Text(e.value),
                    selected: reason == e.key,
                    onSelected: (_) => setSheet(() => reason = e.key),
                  ),
              ]),
              const SizedBox(height: 8),
              TextField(controller: details, maxLength: 1000, maxLines: 3, minLines: 1, decoration: const InputDecoration(hintText: 'Details (optional)')),
              if (recent.isNotEmpty)
                CheckboxListTile(
                  value: includeMessages,
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Include the last 5 messages'),
                  subtitle: const Text('Only these decrypted messages are shared with the report.'),
                  onChanged: (v) => setSheet(() => includeMessages = v ?? false),
                ),
              if (userId != null)
                CheckboxListTile(
                  value: block,
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Also block this person'),
                  onChanged: (v) => setSheet(() => block = v ?? false),
                ),
              const SizedBox(height: 8),
              PrimaryButton(label: 'Send report', onPressed: () => Navigator.pop(ctx, true)),
            ]),
          ),
        ),
      ),
    ),
  );
  if (sent != true || !context.mounted) return;
  final evidence = includeMessages
      ? [
          for (final m in recent.take(5))
            {'id': m.id, 'sender': m.senderId, 'at': m.createdAt.toIso8601String(), 'kind': m.kind, 'text': m.preview()},
        ]
      : null;
  await guard(context, () async {
    await core.sb.from('reports').insert({
      'reported_user_id': ?userId,
      'conversation_id': ?conversationId,
      'reason': reason,
      'details': details.text.trim(),
      'evidence': ?evidence,
    });
    if (block && userId != null) {
      await core.sb.from('user_blocks').upsert({'blocker_id': core.userId, 'blocked_id': userId},
          onConflict: 'blocker_id,blocked_id', ignoreDuplicates: true);
      unawaited(core.chatList.refresh());
    }
  }, success: 'Thanks — your report was sent');
}

Future<String?> uploadAvatar(HimeCore core, String folder) async {
  final x = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 720, maxHeight: 720, imageQuality: 85);
  if (x == null) return null;
  final path = '$folder/${DateTime.now().millisecondsSinceEpoch}.jpg';
  await core.sb.storage.from('avatars').uploadBinary(path, await x.readAsBytes(),
      fileOptions: const FileOptions(contentType: 'image/jpeg', upsert: false));
  SignedUrls.clear();
  return path;
}

// ---------------------------------------------------------------- chat info

class ChatInfoScreen extends ConsumerStatefulWidget {
  const ChatInfoScreen({super.key, required this.conversationId});
  final String conversationId;

  @override
  ConsumerState<ChatInfoScreen> createState() => _ChatInfoScreenState();
}

class _ChatInfoScreenState extends ConsumerState<ChatInfoScreen> {
  late final HimeCore core = ref.read(coreProvider);
  ChatSummary? chat;
  Profile? peer;
  Map<String, dynamic>? group;
  List<Map<String, dynamic>> members = [];
  int mediaCount = 0;
  bool loading = true;
  Object? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      chat = core.chatList.byId(widget.conversationId);
      if (chat == null) {
        await core.chatList.refresh();
        chat = core.chatList.byId(widget.conversationId);
      }
      final c = chat;
      if (c == null) throw StateError('This chat is no longer available.');
      if (c.isGroup) {
        group = await core.sb
            .from('groups')
            .select('name, description, avatar_path, avatar_version, only_admins_send, only_admins_edit_info, only_admins_add, is_announcement')
            .eq('conversation_id', c.id)
            .maybeSingle();
        members = (await core.sb.rpc('get_group_members', params: {'p_conversation_id': c.id}) as List<dynamic>)
            .cast<Map<String, dynamic>>();
        members.sort((a, b) {
          int rank(Map<String, dynamic> m) => m['user_id'] == core.userId ? 0 : (m['role'] == 'owner' ? 1 : (m['role'] == 'admin' ? 2 : 3));
          final r = rank(a).compareTo(rank(b));
          return r != 0 ? r : ((a['display_name'] as String?) ?? '').compareTo((b['display_name'] as String?) ?? '');
        });
      } else if (c.otherUserId != null) {
        peer = await core.profiles.fetch(c.otherUserId!);
      }
      mediaCount = (await core.chats.mediaMessages(conversationId: c.id, kinds: const ['image', 'video', 'document'])).length;
      error = null;
    } catch (e) {
      error = e;
    }
    if (mounted) setState(() => loading = false);
  }

  bool get _isAdmin => chat?.isAdmin ?? false;
  bool get _canEditInfo => chat != null && (group?['only_admins_edit_info'] != true || _isAdmin);
  bool get _canAdd => chat != null && group?['is_announcement'] != true && (group?['only_admins_add'] != true || _isAdmin);

  Future<void> _showSafetyNumber() async {
    final c = chat;
    if (c == null || c.otherUserId == null) return;
    try {
      final rows = (await core.sb.rpc('get_conversation_devices', params: {'p_conversation_id': c.id}) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      final mine = rows.where((r) => r['user_id'] == core.userId).map((r) => r['identity_key'] as String).toList();
      final theirs = rows.where((r) => r['user_id'] == c.otherUserId).map((r) => r['identity_key'] as String).toList();
      final number = E2ee.safetyNumber(core.userId, mine, c.otherUserId!, theirs);
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Verify security code'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.verified_user_rounded, size: 40, color: HimeColors.online),
            const SizedBox(height: 12),
            SelectableText(number,
                textAlign: TextAlign.center, style: const TextStyle(fontFamily: 'monospace', fontSize: 17, letterSpacing: 1.5, height: 1.6)),
            const SizedBox(height: 12),
            Text(
              'Compare this code with ${c.title} in person or on a call. If they match, your messages and calls are end-to-end encrypted between your devices. The code changes when either of you adds a new device.',
              style: ctx.text.bodySmall,
              textAlign: TextAlign.center,
            ),
          ]),
          actions: [
            TextButton(onPressed: () => Clipboard.setData(ClipboardData(text: number)), child: const Text('Copy')),
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Done')),
          ],
        ),
      );
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
  }

  Future<void> _editGroup() async {
    final g = group;
    final c = chat;
    if (g == null || c == null) return;
    await showActionSheet(context, title: 'Edit group', actions: [
      SheetAction(Icons.edit_rounded, 'Change name', () async {
        final name = await promptText(context, title: 'Group name', initial: g['name'] as String?, maxLength: 64);
        if (name == null || name.isEmpty || !mounted) return;
        await guard(context, () async {
          await core.sb.rpc('update_group_info', params: {'p_conversation_id': c.id, 'p_name': name});
          await core.chatList.refresh();
          await _load();
        });
      }),
      SheetAction(Icons.notes_rounded, 'Change description', () async {
        final d = await promptText(context, title: 'Description', initial: g['description'] as String?, maxLength: 512, maxLines: 4);
        if (d == null || !mounted) return;
        await guard(context, () async {
          await core.sb.rpc('update_group_info', params: {'p_conversation_id': c.id, 'p_description': d});
          await _load();
        });
      }),
      SheetAction(Icons.photo_camera_rounded, 'Change photo', () async {
        await guard(context, () async {
          final path = await uploadAvatar(core, 'groups/${c.id}');
          if (path == null) return;
          await core.sb.rpc('update_group_info', params: {'p_conversation_id': c.id, 'p_avatar_path': path});
          await core.chatList.refresh();
          await _load();
        });
      }),
      if (g['avatar_path'] != null)
        SheetAction(Icons.hide_image_outlined, 'Remove photo', () async {
          await guard(context, () async {
            await core.sb.rpc('update_group_info', params: {'p_conversation_id': c.id, 'p_remove_avatar': true});
            await core.chatList.refresh();
            await _load();
          });
        }),
    ]);
  }

  Future<void> _memberActions(Map<String, dynamic> m) async {
    final uid = m['user_id'] as String;
    if (uid == core.userId) return;
    final role = m['role'] as String;
    final name = (m['display_name'] as String?)?.isNotEmpty == true ? m['display_name'] as String : (m['username'] as String? ?? 'Member');
    final myRole = chat?.myRole ?? 'member';
    final canRemove = myRole == 'owner' || (myRole == 'admin' && role != 'owner');
    await showActionSheet(context, title: name, actions: [
      SheetAction(Icons.chat_bubble_outline_rounded, 'Message $name', () => openDirectChat(context, core, uid)),
      SheetAction(Icons.person_outline_rounded, 'View profile', () => context.push('/user/$uid')),
      if (_isAdmin && role == 'member')
        SheetAction(Icons.admin_panel_settings_outlined, 'Make group admin', () async {
          await guard(context, () => core.sb.rpc('set_member_role', params: {'p_conversation_id': chat!.id, 'p_user_id': uid, 'p_admin': true}));
          await _load();
        }),
      if (_isAdmin && role == 'admin')
        SheetAction(Icons.remove_moderator_outlined, 'Dismiss as admin', () async {
          await guard(context, () => core.sb.rpc('set_member_role', params: {'p_conversation_id': chat!.id, 'p_user_id': uid, 'p_admin': false}));
          await _load();
        }),
      if (canRemove)
        SheetAction(Icons.person_remove_outlined, 'Remove $name', () async {
          final ok = await confirm(context, title: 'Remove $name from the group?', confirmLabel: 'Remove', danger: true);
          if (!ok || !mounted) return;
          await guard(context, () => core.sb.from('conversation_members').delete().eq('conversation_id', chat!.id).eq('user_id', uid));
          await _load();
        }, danger: true),
    ]);
  }

  Future<void> _exitGroup() async {
    final c = chat;
    if (c == null) return;
    final ok = await confirm(context,
        title: 'Exit "${c.title}"?',
        message: c.myRole == 'owner' ? 'Ownership will pass to another admin or member.' : null,
        confirmLabel: 'Exit',
        danger: true);
    if (!ok || !mounted) return;
    final done = await guard(context, () async {
      await core.sb.from('conversation_members').delete().eq('conversation_id', c.id).eq('user_id', core.userId);
      await core.chatList.refresh();
    });
    if (done && mounted) context.go('/chats');
  }

  @override
  Widget build(BuildContext context) {
    final c = chat;
    return Scaffold(
      appBar: AppBar(title: Text(c?.isGroup == true ? 'Group info' : 'Contact info'), actions: [
        if (c?.isGroup == true && _canEditInfo) IconButton(tooltip: 'Edit', onPressed: _editGroup, icon: const Icon(Icons.edit_outlined)),
      ]),
      body: loading
          ? const CenteredLoader()
          : error != null || c == null
              ? ErrorState(error: error ?? 'Not found', onRetry: _load)
              : RefreshIndicator(onRefresh: _load, child: c.isGroup ? _groupBody(c) : _directBody(c)),
    );
  }

  Widget _header({required String title, String? subtitle, String? path, int version = 0, IconData? icon, String? about}) {
    return Column(children: [
      const SizedBox(height: 16),
      Hero(
        tag: 'avatar-${widget.conversationId}',
        child: HimeAvatar(name: title, path: path, version: version, size: 112, icon: icon),
      ),
      const SizedBox(height: 14),
      Text(title, style: context.text.headlineSmall, textAlign: TextAlign.center),
      if (subtitle != null) ...[
        const SizedBox(height: 4),
        Text(subtitle, style: context.text.bodyMedium?.copyWith(color: context.palette.muted)),
      ],
      if (about != null && about.isNotEmpty)
        Padding(
          padding: const EdgeInsets.fromLTRB(32, 10, 32, 0),
          child: Text(about, textAlign: TextAlign.center, style: context.text.bodyMedium),
        ),
      const SizedBox(height: 16),
    ]);
  }

  Widget _actionButton(IconData icon, String label, VoidCallback? onTap) => Expanded(
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

  Widget _commonTiles(ChatSummary c) => SettingsGroup(children: [
        SettingsTile(
          icon: Icons.perm_media_outlined,
          title: 'Media, links and docs',
          trailing: Text('$mediaCount', style: context.text.labelLarge),
          onTap: () => context.push('/chat/${c.id}/media'),
        ),
        SettingsTile(
          icon: c.isMuted ? Icons.notifications_off_outlined : Icons.notifications_none_rounded,
          title: 'Mute notifications',
          subtitle: c.isMuted ? 'Muted until ${Fmt.chatTime(c.mutedUntil!)}' : null,
          trailing: Switch(
            value: c.isMuted,
            onChanged: (v) async {
              if (v) {
                final d = await pickMuteDuration(context);
                if (d == null || !mounted) return;
                await guard(context, () => core.chatList.setMuted(c.id, d));
              } else {
                await guard(context, () => core.chatList.setMuted(c.id, null));
              }
              if (mounted) setState(() => chat = core.chatList.byId(c.id));
            },
          ),
        ),
        SettingsTile(
          icon: Icons.lock_outline_rounded,
          title: 'Encryption',
          subtitle: c.isGroup
              ? 'Messages and calls are end-to-end encrypted.'
              : 'Messages and calls are end-to-end encrypted. Tap to verify.',
          onTap: c.isGroup ? null : _showSafetyNumber,
        ),
      ]);

  Widget _directBody(ChatSummary c) {
    final p = peer;
    final peerId = c.otherUserId;
    return ListView(children: [
      _header(
        title: p?.name ?? c.title,
        subtitle: p?.username == null ? null : '@${p!.username}',
        path: p?.avatarPath ?? c.avatarPath,
        version: p?.avatarVersion ?? c.avatarVersion,
        about: p?.about,
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Row(children: [
          _actionButton(Icons.call_outlined, 'Voice', c.blockedByMe || peerId == null
              ? null
              : () => core.calls.startCall(conversationId: c.id, peerId: peerId, peerName: c.title, video: false).catchError((Object e) {
                    if (mounted) toast(context, friendlyError(e));
                  })),
          _actionButton(Icons.videocam_outlined, 'Video', c.blockedByMe || peerId == null
              ? null
              : () => core.calls.startCall(conversationId: c.id, peerId: peerId, peerName: c.title, video: true).catchError((Object e) {
                    if (mounted) toast(context, friendlyError(e));
                  })),
          _actionButton(Icons.search_rounded, 'Search', () => context.push('/chat/${c.id}/search')),
        ]),
      ),
      const SizedBox(height: 8),
      _commonTiles(c),
      if (peerId != null)
        SettingsGroup(children: [
          SettingsTile(icon: Icons.person_outline_rounded, title: 'View full profile', onTap: () => context.push('/user/$peerId')),
          SettingsTile(
            icon: Icons.block_rounded,
            title: c.blockedByMe ? 'Unblock ${c.title}' : 'Block ${c.title}',
            danger: !c.blockedByMe,
            onTap: () async {
              await toggleBlock(context, core, peerId, c.blockedByMe);
              await core.chatList.refresh();
              await _load();
            },
          ),
          SettingsTile(
            icon: Icons.thumb_down_alt_outlined,
            title: 'Report ${c.title}',
            danger: true,
            onTap: () => showReportSheet(context, core, userId: peerId, conversationId: c.id),
          ),
        ]),
      const SizedBox(height: 32),
    ]);
  }

  Widget _groupBody(ChatSummary c) {
    final g = group ?? {};
    final announcement = g['is_announcement'] == true;
    return ListView(children: [
      _header(
        title: (g['name'] as String?) ?? c.title,
        subtitle: 'Group · ${members.length} members',
        path: g['avatar_path'] as String?,
        version: (g['avatar_version'] as num?)?.toInt() ?? 0,
        icon: Icons.groups_rounded,
        about: g['description'] as String?,
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Row(children: [
          _actionButton(Icons.person_add_alt_outlined, 'Add', _canAdd ? () => context.push('/group/${c.id}/add').then((_) => _load()) : null),
          _actionButton(Icons.link_rounded, 'Invite', _isAdmin && !announcement ? () => context.push('/group/${c.id}/invite') : null),
          _actionButton(Icons.search_rounded, 'Search', () => context.push('/chat/${c.id}/search')),
        ]),
      ),
      const SizedBox(height: 8),
      _commonTiles(c),
      if (_isAdmin)
        SettingsGroup(title: 'Group permissions', children: [
          SwitchListTile(
            secondary: const Icon(Icons.campaign_outlined),
            title: const Text('Only admins can send messages'),
            value: g['only_admins_send'] == true || announcement,
            onChanged: announcement
                ? null
                : (v) async {
                    await guard(context, () => core.sb.rpc('update_group_settings', params: {'p_conversation_id': c.id, 'p_only_admins_send': v}));
                    await core.chatList.refresh();
                    await _load();
                  },
          ),
          SwitchListTile(
            secondary: const Icon(Icons.edit_note_rounded),
            title: const Text('Only admins can edit group info'),
            value: g['only_admins_edit_info'] == true,
            onChanged: (v) async {
              await guard(context, () => core.sb.rpc('update_group_settings', params: {'p_conversation_id': c.id, 'p_only_admins_edit_info': v}));
              await _load();
            },
          ),
          SwitchListTile(
            secondary: const Icon(Icons.group_add_outlined),
            title: const Text('Only admins can add members'),
            value: g['only_admins_add'] == true || announcement,
            onChanged: announcement
                ? null
                : (v) async {
                    await guard(context, () => core.sb.rpc('update_group_settings', params: {'p_conversation_id': c.id, 'p_only_admins_add': v}));
                    await _load();
                  },
          ),
        ]),
      SettingsGroup(title: '${members.length} members', children: [
        for (final m in members)
          ListTile(
            leading: HimeAvatar(
              name: (m['display_name'] as String?) ?? '',
              path: m['avatar_path'] as String?,
              version: (m['avatar_version'] as num?)?.toInt() ?? 0,
              size: 42,
            ),
            title: Text(m['user_id'] == core.userId
                ? 'You'
                : ((m['display_name'] as String?)?.isNotEmpty == true ? m['display_name'] as String : (m['username'] as String? ?? 'Member'))),
            subtitle: m['username'] == null ? null : Text('@${m['username']}'),
            trailing: m['role'] == 'member'
                ? null
                : Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(color: HimeColors.yellowSoft, borderRadius: BorderRadius.circular(8)),
                    child: Text(m['role'] == 'owner' ? 'Owner' : 'Admin',
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: HimeColors.ink)),
                  ),
            onTap: () => _memberActions(m),
          ),
      ]),
      SettingsGroup(children: [
        SettingsTile(icon: Icons.logout_rounded, title: 'Exit group', danger: true, onTap: _exitGroup),
        SettingsTile(
          icon: Icons.thumb_down_alt_outlined,
          title: 'Report group',
          danger: true,
          onTap: () => showReportSheet(context, core, conversationId: c.id),
        ),
      ]),
      const SizedBox(height: 32),
    ]);
  }
}

// ---------------------------------------------------------------- media gallery

class MediaGalleryScreen extends ConsumerStatefulWidget {
  const MediaGalleryScreen({super.key, required this.conversationId});
  final String conversationId;

  @override
  ConsumerState<MediaGalleryScreen> createState() => _MediaGalleryScreenState();
}

class _MediaGalleryScreenState extends ConsumerState<MediaGalleryScreen> {
  late final HimeCore core = ref.read(coreProvider);
  List<ChatMessage>? media, docs, links;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final m = await core.chats.mediaMessages(conversationId: widget.conversationId);
    final d = await core.chats.mediaMessages(conversationId: widget.conversationId, kinds: const ['document', 'voice', 'audio']);
    final t = await core.chats.mediaMessages(conversationId: widget.conversationId, kinds: const ['text']);
    if (!mounted) return;
    setState(() {
      media = m;
      docs = d;
      links = t.where((x) => findUrls(x.text).isNotEmpty && !x.isDeleted).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Media, links and docs'),
          bottom: const TabBar(tabs: [Tab(text: 'Media'), Tab(text: 'Docs'), Tab(text: 'Links')]),
        ),
        body: media == null
            ? const CenteredLoader()
            : TabBarView(children: [
                media!.isEmpty
                    ? const EmptyState(icon: Icons.photo_library_outlined, title: 'No media', message: 'Photos and videos you share appear here.')
                    : GridView.builder(
                        padding: const EdgeInsets.all(2),
                        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 3, mainAxisSpacing: 2, crossAxisSpacing: 2),
                        itemCount: media!.length,
                        itemBuilder: (_, i) => ClipRect(
                          child: FittedBox(fit: BoxFit.cover, clipBehavior: Clip.hardEdge, child: MediaThumb(message: media![i], core: core)),
                        ),
                      ),
                docs!.isEmpty
                    ? const EmptyState(icon: Icons.description_outlined, title: 'No documents', message: 'Documents and voice messages appear here.')
                    : ListView(padding: const EdgeInsets.all(12), children: [
                        for (final m in docs!)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: m.kind == 'document'
                                ? DocumentTile(message: m, core: core)
                                : VoiceMessage(message: m, core: core, color: context.colors.onSurface),
                          ),
                      ]),
                links!.isEmpty
                    ? const EmptyState(icon: Icons.link_rounded, title: 'No links', message: 'Links shared in this chat appear here.')
                    : ListView(children: [
                        for (final m in links!)
                          for (final u in findUrls(m.text))
                            ListTile(
                              leading: const CircleAvatar(backgroundColor: HimeColors.yellowSoft, child: Icon(Icons.link_rounded, color: HimeColors.ink)),
                              title: Text(u, maxLines: 1, overflow: TextOverflow.ellipsis),
                              subtitle: Text('${core.profiles.nameOf(m.senderId)} · ${Fmt.chatTime(m.createdAt)}'),
                              onTap: () => Clipboard.setData(ClipboardData(text: u)).then((_) {
                                if (context.mounted) toast(context, 'Link copied');
                              }),
                            ),
                      ]),
              ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- search in chat

class ChatSearchScreen extends ConsumerStatefulWidget {
  const ChatSearchScreen({super.key, required this.conversationId});
  final String conversationId;

  @override
  ConsumerState<ChatSearchScreen> createState() => _ChatSearchScreenState();
}

class _ChatSearchScreenState extends ConsumerState<ChatSearchScreen> {
  late final HimeCore core = ref.read(coreProvider);
  final _q = TextEditingController();
  final _debounce = Debouncer(const Duration(milliseconds: 250));
  List<ChatMessage> results = [];
  bool searched = false;

  @override
  void dispose() {
    _q.dispose();
    _debounce.dispose();
    super.dispose();
  }

  void _search(String v) => _debounce(() async {
        final r = await core.chats.search(v, conversationId: widget.conversationId);
        if (mounted) {
          setState(() {
            results = r;
            searched = v.trim().isNotEmpty;
          });
        }
      });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: TextField(
          controller: _q,
          autofocus: true,
          onChanged: _search,
          decoration: const InputDecoration(
            hintText: 'Search messages',
            filled: false,
            border: InputBorder.none,
            enabledBorder: InputBorder.none,
            focusedBorder: InputBorder.none,
          ),
        ),
      ),
      body: results.isEmpty
          ? EmptyState(
              icon: Icons.manage_search_rounded,
              title: searched ? 'No messages found' : 'Search this chat',
              message: 'Search happens on your phone — your messages are never sent anywhere to be searched.',
            )
          : ListView.separated(
              itemCount: results.length,
              separatorBuilder: (_, __) => const Divider(height: 1, indent: 72),
              itemBuilder: (context, i) {
                final m = results[i];
                return ListTile(
                  leading: HimeAvatar(name: core.profiles.nameOf(m.senderId), path: core.profiles.cached(m.senderId)?.avatarPath, size: 40),
                  title: Text(core.profiles.nameOf(m.senderId)),
                  subtitle: _Highlight(text: m.preview(), query: _q.text.trim()),
                  trailing: Text(Fmt.chatTime(m.createdAt), style: context.text.labelSmall),
                  onTap: () => context.pop(),
                );
              },
            ),
    );
  }
}

class _Highlight extends StatelessWidget {
  const _Highlight({required this.text, required this.query});
  final String text;
  final String query;

  @override
  Widget build(BuildContext context) {
    final i = query.isEmpty ? -1 : text.toLowerCase().indexOf(query.toLowerCase());
    if (i < 0) return Text(text, maxLines: 2, overflow: TextOverflow.ellipsis);
    return Text.rich(
      TextSpan(children: [
        TextSpan(text: text.substring(0, i)),
        TextSpan(
          text: text.substring(i, i + query.length),
          style: const TextStyle(backgroundColor: HimeColors.yellowSoft, color: HimeColors.ink, fontWeight: FontWeight.w700),
        ),
        TextSpan(text: text.substring(i + query.length)),
      ]),
      maxLines: 2,
      overflow: TextOverflow.ellipsis,
    );
  }
}

// ---------------------------------------------------------------- new chat

class NewChatScreen extends ConsumerWidget {
  const NewChatScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final core = ref.watch(coreProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('New chat')),
      body: PeoplePicker(
        core: core,
        onPick: (p) => openDirectChat(context, core, p.id, replace: true),
        header: [
          _NewTile(icon: Icons.group_add_rounded, label: 'New group', onTap: () => context.pushReplacement('/new-group')),
          _NewTile(icon: Icons.groups_rounded, label: 'New community', onTap: () => context.pushReplacement('/community/new')),
          _NewTile(icon: Icons.person_add_alt_1_rounded, label: 'Contacts', onTap: () => context.push('/contacts')),
          _NewTile(icon: Icons.qr_code_rounded, label: 'Join with an invite code', onTap: () => context.push('/join')),
        ],
      ),
    );
  }
}

class _NewTile extends StatelessWidget {
  const _NewTile({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ListTile(
        leading: CircleAvatar(backgroundColor: HimeColors.yellow, child: Icon(icon, color: HimeColors.ink)),
        title: Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
        onTap: onTap,
      );
}

// ---------------------------------------------------------------- forward

class ForwardScreen extends ConsumerStatefulWidget {
  const ForwardScreen({super.key, required this.messages});
  final ForwardArgs messages;

  @override
  ConsumerState<ForwardScreen> createState() => _ForwardScreenState();
}

class _ForwardScreenState extends ConsumerState<ForwardScreen> {
  late final HimeCore core = ref.read(coreProvider);
  final selected = <String>{};
  bool sending = false;
  String query = '';

  Future<void> _send() async {
    setState(() => sending = true);
    try {
      for (final convId in selected) {
        for (final m in widget.messages.messages) {
          final payload = Map<String, dynamic>.from(m.payload ?? const {})
            ..remove('reply')
            ..remove('v')
            ..remove('t');
          if (m.media != null) {
            // Media keys are per-file; re-encrypt for the new chat.
            final file = await core.chats.mediaFile(m);
            if (file == null) continue;
            final media = Map<String, dynamic>.from(m.media!)
              ..remove('path')
              ..remove('key')
              ..remove('nonce')
              ..remove('enc')
              ..remove('size')
              ..remove('mime')
              ..remove('name');
            await core.chats.sendMedia(convId, m.kind, file,
                caption: m.text.isEmpty ? null : m.text,
                name: m.media!['name'] as String?,
                mime: m.media!['mime'] as String?,
                extra: media,
                forwarded: true);
          } else {
            await core.chats.sendPayload(convId, m.kind, {...payload, 'fwd': true});
          }
        }
      }
      if (!mounted) return;
      toast(context, 'Forwarded');
      if (selected.length == 1) {
        context.pushReplacement('/chat/${selected.first}');
      } else {
        context.pop();
      }
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => sending = false);
  }

  @override
  Widget build(BuildContext context) {
    final chats = core.chatList.chats
        .where((c) => c.canSend && !c.blockedByMe)
        .where((c) => query.isEmpty || c.title.toLowerCase().contains(query.toLowerCase()))
        .toList();
    return Scaffold(
      appBar: AppBar(title: Text(selected.isEmpty ? 'Forward to…' : '${selected.length} selected')),
      floatingActionButton: selected.isEmpty
          ? null
          : FloatingActionButton(
              onPressed: sending ? null : _send,
              child: sending ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4)) : const Icon(Icons.send_rounded),
            ),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
          child: TextField(
            onChanged: (v) => setState(() => query = v.trim()),
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded), hintText: 'Search chats'),
          ),
        ),
        Expanded(
          child: ListView.builder(
            itemCount: chats.length,
            itemBuilder: (_, i) {
              final c = chats[i];
              final on = selected.contains(c.id);
              return ListTile(
                leading: HimeAvatar(name: c.title, path: c.avatarPath, version: c.avatarVersion, size: 44, icon: c.isGroup ? Icons.groups_rounded : null),
                title: Text(c.title),
                trailing: Icon(on ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                    color: on ? HimeColors.yellowDeep : context.palette.muted),
                onTap: () => setState(() {
                  if (on) {
                    selected.remove(c.id);
                  } else if (selected.length < 5) {
                    selected.add(c.id);
                  } else {
                    toast(context, 'You can forward to up to 5 chats at a time');
                  }
                }),
              );
            },
          ),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- message info

class MessageInfoScreen extends ConsumerStatefulWidget {
  const MessageInfoScreen({super.key, required this.args});
  final MessageInfoArgs args;

  @override
  ConsumerState<MessageInfoScreen> createState() => _MessageInfoScreenState();
}

class _MessageInfoScreenState extends ConsumerState<MessageInfoScreen> {
  late final HimeCore core = ref.read(coreProvider);
  List<Map<String, dynamic>>? receipts;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final rows = await core.sb
          .from('message_receipts')
          .select('user_id, delivered, read')
          .eq('message_id', widget.args.message.id)
          .neq('user_id', core.userId);
      await core.profiles.ensure(rows.map((r) => r['user_id'] as String?));
      if (mounted) setState(() => receipts = rows);
    } catch (e) {
      if (mounted) setState(() => receipts = []);
    }
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.args.message;
    final read = receipts?.where((r) => r['read'] == true).toList() ?? [];
    final delivered = receipts?.where((r) => r['delivered'] == true && r['read'] != true).toList() ?? [];
    final pending = receipts?.where((r) => r['delivered'] != true).toList() ?? [];
    Widget section(String title, IconData icon, Color color, List<Map<String, dynamic>> rows) => SettingsGroup(
          title: title,
          children: rows.isEmpty
              ? [ListTile(dense: true, title: Text('No one yet', style: TextStyle(color: context.palette.muted)))]
              : [
                  for (final r in rows)
                    ListTile(
                      leading: HimeAvatar(name: core.profiles.nameOf(r['user_id'] as String), path: core.profiles.cached(r['user_id'] as String)?.avatarPath, size: 38),
                      title: Text(core.profiles.nameOf(r['user_id'] as String)),
                      trailing: Icon(icon, color: color, size: 20),
                    ),
                ],
        );
    return Scaffold(
      appBar: AppBar(title: const Text('Message info')),
      body: ListView(padding: const EdgeInsets.only(top: 12), children: [
        IgnorePointer(
          child: MessageBubble(
            message: m,
            core: core,
            isMine: true,
            delivery: Delivery.sent,
            showSender: false,
            groupedWithNext: false,
          ),
        ),
        ListTile(leading: const Icon(Icons.schedule_rounded), title: const Text('Sent'), trailing: Text('${Fmt.dayLabel(m.createdAt)}, ${Fmt.time(m.createdAt)}')),
        if (m.editedAt != null)
          ListTile(leading: const Icon(Icons.edit_rounded), title: const Text('Edited'), trailing: Text('${Fmt.dayLabel(m.editedAt!)}, ${Fmt.time(m.editedAt!)}')),
        if (receipts == null)
          const Padding(padding: EdgeInsets.all(24), child: CenteredLoader())
        else ...[
          section('Read by', Icons.done_all_rounded, HimeColors.read, read),
          section('Delivered to', Icons.done_all_rounded, context.palette.muted, delivered),
          if (pending.isNotEmpty) section('Not delivered yet', Icons.done_rounded, context.palette.muted, pending),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text('People who turned off read receipts appear as delivered.',
                style: context.text.bodySmall?.copyWith(color: context.palette.muted)),
          ),
        ],
      ]),
    );
  }
}

// ---------------------------------------------------------------- media viewer

class MediaViewerScreen extends StatefulWidget {
  const MediaViewerScreen({super.key, required this.args});
  final MediaViewerArgs args;

  @override
  State<MediaViewerScreen> createState() => _MediaViewerScreenState();
}

class _MediaViewerScreenState extends State<MediaViewerScreen> {
  VideoPlayerController? _video;
  bool _chrome = true;

  @override
  void initState() {
    super.initState();
    if (widget.args.isVideo) {
      _video = VideoPlayerController.file(widget.args.file)
        ..initialize().then((_) {
          if (mounted) {
            setState(() {});
            _video!.play();
          }
        });
      _video!.addListener(_onVideo);
    }
  }

  void _onVideo() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _video?.removeListener(_onVideo);
    _video?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final v = _video;
    Widget content;
    if (v != null) {
      content = v.value.isInitialized
          ? AspectRatio(aspectRatio: v.value.aspectRatio, child: VideoPlayer(v))
          : const CircularProgressIndicator(color: Colors.white);
    } else {
      content = InteractiveViewer(
        maxScale: 5,
        child: Image.file(widget.args.file, fit: BoxFit.contain, errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_outlined, color: Colors.white54, size: 64)),
      );
    }
    if (widget.args.heroTag != null) content = Hero(tag: widget.args.heroTag!, child: content);
    return Scaffold(
      backgroundColor: Colors.black,
      extendBodyBehindAppBar: true,
      appBar: _chrome
          ? AppBar(
              backgroundColor: Colors.black45,
              foregroundColor: Colors.white,
              actions: [
                IconButton(
                  tooltip: 'Share',
                  icon: const Icon(Icons.share_rounded),
                  onPressed: () => openLocalFile(context, widget.args.file, null),
                ),
              ],
            )
          : null,
      body: GestureDetector(
        onTap: () {
          if (v != null && v.value.isInitialized) {
            v.value.isPlaying ? v.pause() : v.play();
          }
          setState(() => _chrome = !_chrome);
        },
        child: Stack(children: [
          Positioned.fill(child: Center(child: content)),
          if (v != null && v.value.isInitialized && _chrome)
            Positioned(
              left: 16,
              right: 16,
              bottom: 24,
              child: SafeArea(
                child: Column(children: [
                  VideoProgressIndicator(v, allowScrubbing: true, colors: const VideoProgressColors(playedColor: HimeColors.yellow)),
                  const SizedBox(height: 8),
                  Row(children: [
                    Icon(v.value.isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded, color: Colors.white),
                    const SizedBox(width: 8),
                    Text('${Fmt.duration(v.value.position)} / ${Fmt.duration(v.value.duration)}', style: const TextStyle(color: Colors.white)),
                  ]),
                ]),
              ),
            ),
          if ((widget.args.caption ?? '').isNotEmpty && _chrome && v == null)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Container(
                color: Colors.black54,
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 28),
                child: SafeArea(top: false, child: Text(widget.args.caption!, style: const TextStyle(color: Colors.white, fontSize: 15))),
              ),
            ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- starred & archived

class StarredScreen extends ConsumerStatefulWidget {
  const StarredScreen({super.key});

  @override
  ConsumerState<StarredScreen> createState() => _StarredScreenState();
}

class _StarredScreenState extends ConsumerState<StarredScreen> {
  late final HimeCore core = ref.read(coreProvider);
  late Future<List<ChatMessage>> _future = core.chats.allStarred();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Starred messages')),
      body: FutureBuilder<List<ChatMessage>>(
        future: _future,
        builder: (context, snap) {
          if (snap.hasError) return ErrorState(error: snap.error!, onRetry: () => setState(() => _future = core.chats.allStarred()));
          if (!snap.hasData) return const CenteredLoader();
          final list = snap.data!;
          if (list.isEmpty) {
            return const EmptyState(
              icon: Icons.star_outline_rounded,
              title: 'No starred messages',
              message: 'Long-press a message and tap Star to find it here later.',
            );
          }
          return ListView.builder(
            itemCount: list.length,
            itemBuilder: (context, i) {
              final m = list[i];
              final chat = core.chatList.byId(m.conversationId);
              return InkWell(
                onTap: () => context.push('/chat/${m.conversationId}'),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 4, 16, 2),
                      child: Text(
                        '${core.profiles.nameOf(m.senderId)}${chat == null ? '' : ' · ${chat.title}'} · ${Fmt.chatTime(m.createdAt)}',
                        style: context.text.labelMedium?.copyWith(color: context.palette.muted),
                      ),
                    ),
                    IgnorePointer(
                      child: MessageBubble(
                        message: m,
                        core: core,
                        isMine: m.senderId == core.userId,
                        delivery: Delivery.sent,
                        showSender: false,
                        groupedWithNext: false,
                        starred: true,
                      ),
                    ),
                  ]),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class ArchivedScreen extends ConsumerWidget {
  const ArchivedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final core = ref.watch(coreProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Archived')),
      body: ListenableBuilder(
        listenable: core.chatList,
        builder: (context, _) {
          final list = core.chatList.archived;
          if (list.isEmpty) {
            return const EmptyState(
              icon: Icons.archive_outlined,
              title: 'No archived chats',
              message: 'Long-press a chat and choose Archive to tuck it away here.',
            );
          }
          return ListView.builder(itemCount: list.length, itemBuilder: (_, i) => ChatTile(chat: list[i], core: core));
        },
      ),
    );
  }
}
