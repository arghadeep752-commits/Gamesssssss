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
import '../chats/models.dart';
import '../contacts/contacts.dart';

String inviteLink(String code, {bool community = false}) =>
    '${AppConfig.instance.inviteBaseUrl}?code=$code${community ? '&c=1' : ''}';

/// Extracts an invite code from a pasted link or a bare code.
String? parseInviteCode(String input) {
  final s = input.trim();
  if (s.isEmpty) return null;
  final uri = Uri.tryParse(s);
  final fromQuery = uri?.queryParameters['code'];
  if (fromQuery != null && fromQuery.isNotEmpty) return fromQuery;
  final m = RegExp(r'^[A-Za-z0-9_-]{6,64}$').firstMatch(s);
  return m?.group(0);
}

class CreateGroupScreen extends ConsumerStatefulWidget {
  const CreateGroupScreen({super.key, this.communityId});
  final String? communityId;

  @override
  ConsumerState<CreateGroupScreen> createState() => _CreateGroupScreenState();
}

class _CreateGroupScreenState extends ConsumerState<CreateGroupScreen> {
  late final HimeCore core = ref.read(coreProvider);
  List<Profile> members = [];
  bool details = false;
  final _name = TextEditingController();
  final _desc = TextEditingController();
  bool creating = false;

  @override
  void dispose() {
    _name.dispose();
    _desc.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final name = _name.text.trim();
    if (name.isEmpty) {
      toast(context, 'Give your group a name');
      return;
    }
    setState(() => creating = true);
    try {
      final res = Map<String, dynamic>.from(await core.sb.rpc('create_group', params: {
        'p_name': name,
        'p_description': _desc.text.trim(),
        'p_member_ids': members.map((m) => m.id).toList(),
        'p_community_id': widget.communityId,
      }) as Map);
      final id = res['conversation_id'] as String;
      final skipped = (res['skipped'] as List?)?.length ?? 0;
      await core.chatList.refresh();
      if (!mounted) return;
      if (skipped > 0) toast(context, '$skipped person(s) couldn\'t be added because of their privacy settings');
      context.pushReplacement('/chat/$id');
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => creating = false);
  }

  @override
  Widget build(BuildContext context) {
    if (!details) {
      return Scaffold(
        appBar: AppBar(
          title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('New group'),
            Text(members.isEmpty ? 'Add members' : '${members.length} selected', style: context.text.labelMedium),
          ]),
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: () => setState(() => details = true),
          child: const Icon(Icons.arrow_forward_rounded),
        ),
        body: PeoplePicker(core: core, multi: true, initial: members, onSelectionChanged: (s) => setState(() => members = s)),
      );
    }
    return Scaffold(
      appBar: AppBar(
        leading: BackButton(onPressed: () => setState(() => details = false)),
        title: const Text('Group details'),
      ),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        Row(children: [
          const CircleAvatar(radius: 30, backgroundColor: HimeColors.yellowSoft, child: Icon(Icons.groups_rounded, color: HimeColors.ink, size: 30)),
          const SizedBox(width: 16),
          Expanded(child: HimeField(controller: _name, label: 'Group name', maxLength: 64, autofocus: true, textCapitalization: TextCapitalization.sentences)),
        ]),
        const SizedBox(height: 12),
        HimeField(controller: _desc, label: 'Description (optional)', maxLength: 512, maxLines: 3, textCapitalization: TextCapitalization.sentences),
        const SizedBox(height: 8),
        Text('You can add a group photo from Group info after creating it.', style: context.text.bodySmall?.copyWith(color: context.palette.muted)),
        const SizedBox(height: 20),
        Text('Members: ${members.length + 1}', style: context.text.titleSmall),
        const SizedBox(height: 8),
        Wrap(spacing: 10, runSpacing: 10, children: [
          for (final m in members)
            Chip(
              avatar: HimeAvatar(name: m.name, path: m.avatarPath, version: m.avatarVersion, size: 24),
              label: Text(m.name),
            ),
        ]),
        const SizedBox(height: 28),
        PrimaryButton(label: 'Create group', icon: Icons.check_rounded, loading: creating, onPressed: creating ? null : _create),
      ]),
    );
  }
}

class AddMembersScreen extends ConsumerStatefulWidget {
  const AddMembersScreen({super.key, required this.conversationId});
  final String conversationId;

  @override
  ConsumerState<AddMembersScreen> createState() => _AddMembersScreenState();
}

class _AddMembersScreenState extends ConsumerState<AddMembersScreen> {
  late final HimeCore core = ref.read(coreProvider);
  Set<String>? existing;
  List<Profile> selected = [];
  bool adding = false;

  @override
  void initState() {
    super.initState();
    core.sb.rpc('get_group_members', params: {'p_conversation_id': widget.conversationId}).then((rows) {
      if (mounted) setState(() => existing = {for (final r in rows as List) (r as Map)['user_id'] as String});
    }, onError: (Object e) {
      if (mounted) setState(() => existing = {});
    });
  }

  Future<void> _add() async {
    setState(() => adding = true);
    try {
      final res = Map<String, dynamic>.from(await core.sb.rpc('add_group_members', params: {
        'p_conversation_id': widget.conversationId,
        'p_user_ids': selected.map((s) => s.id).toList(),
      }) as Map);
      final skipped = (res['skipped'] as List?)?.length ?? 0;
      if (!mounted) return;
      toast(context, skipped > 0 ? 'Added. $skipped person(s) couldn\'t be added because of their privacy settings.' : 'Members added');
      context.pop();
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => adding = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(selected.isEmpty ? 'Add members' : '${selected.length} selected')),
      floatingActionButton: selected.isEmpty
          ? null
          : FloatingActionButton(
              onPressed: adding ? null : _add,
              child: adding ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4)) : const Icon(Icons.check_rounded),
            ),
      body: existing == null
          ? const CenteredLoader()
          : PeoplePicker(core: core, multi: true, exclude: existing!, onSelectionChanged: (s) => setState(() => selected = s)),
    );
  }
}

class GroupInviteScreen extends ConsumerStatefulWidget {
  const GroupInviteScreen({super.key, required this.conversationId});
  final String conversationId;

  @override
  ConsumerState<GroupInviteScreen> createState() => _GroupInviteScreenState();
}

class _GroupInviteScreenState extends ConsumerState<GroupInviteScreen> {
  late final HimeCore core = ref.read(coreProvider);
  String? code;
  Object? error;

  @override
  void initState() {
    super.initState();
    _load(false);
  }

  Future<void> _load(bool reset) async {
    try {
      final c = await core.sb.rpc('get_group_invite', params: {'p_conversation_id': widget.conversationId, 'p_reset': reset}) as String;
      if (mounted) setState(() => code = c);
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = core.chatList.byId(widget.conversationId)?.title ?? 'Group';
    return Scaffold(
      appBar: AppBar(title: const Text('Invite to group')),
      body: error != null
          ? ErrorState(error: error!, onRetry: () => _load(false))
          : code == null
              ? const CenteredLoader()
              : InviteCard(
                  title: title,
                  subtitle: 'Anyone with this link or code can join this group. Only share it with people you trust.',
                  code: code!,
                  link: inviteLink(code!),
                  onReset: () async {
                    final ok = await confirm(context,
                        title: 'Reset link?', message: 'The current link and code will stop working.', confirmLabel: 'Reset', danger: true);
                    if (ok) await _load(true);
                  },
                ),
    );
  }
}

/// QR + link + code, shared by group and community invites.
class InviteCard extends StatelessWidget {
  const InviteCard({super.key, required this.title, required this.subtitle, required this.code, required this.link, this.onReset});
  final String title;
  final String subtitle;
  final String code;
  final String link;
  final VoidCallback? onReset;

  @override
  Widget build(BuildContext context) {
    final shareText = 'Join "$title" on Hime: $link\nOr open Hime → New chat → Join with an invite code and enter: $code';
    return ListView(padding: const EdgeInsets.all(24), children: [
      Center(
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24), border: Border.all(color: context.palette.border)),
          child: QrImageView(
            data: link,
            size: 220,
            eyeStyle: const QrEyeStyle(eyeShape: QrEyeShape.circle, color: HimeColors.ink),
            dataModuleStyle: const QrDataModuleStyle(dataModuleShape: QrDataModuleShape.circle, color: HimeColors.ink),
          ),
        ),
      ),
      const SizedBox(height: 20),
      Text(title, textAlign: TextAlign.center, style: context.text.titleLarge),
      const SizedBox(height: 6),
      Text(subtitle, textAlign: TextAlign.center, style: context.text.bodyMedium?.copyWith(color: context.palette.muted)),
      const SizedBox(height: 20),
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(color: context.colors.surfaceContainer, borderRadius: BorderRadius.circular(14)),
        child: Row(children: [
          Expanded(child: SelectableText(code, style: const TextStyle(fontFamily: 'monospace', fontSize: 18, letterSpacing: 2))),
          IconButton(
            tooltip: 'Copy code',
            icon: const Icon(Icons.copy_rounded),
            onPressed: () {
              Clipboard.setData(ClipboardData(text: code));
              toast(context, 'Code copied');
            },
          ),
        ]),
      ),
      const SizedBox(height: 16),
      PrimaryButton(
        label: 'Share invite',
        icon: Icons.share_rounded,
        onPressed: () => SharePlus.instance.share(ShareParams(text: shareText, subject: 'Join $title on Hime')),
      ),
      const SizedBox(height: 8),
      OutlinedButton.icon(
        onPressed: () {
          Clipboard.setData(ClipboardData(text: link));
          toast(context, 'Link copied');
        },
        icon: const Icon(Icons.link_rounded),
        label: const Text('Copy link'),
      ),
      if (onReset != null) ...[
        const SizedBox(height: 8),
        TextButton.icon(
          onPressed: onReset,
          icon: Icon(Icons.restart_alt_rounded, color: context.colors.error),
          label: Text('Reset link', style: TextStyle(color: context.colors.error)),
        ),
      ],
    ]);
  }
}

class JoinInviteScreen extends ConsumerStatefulWidget {
  const JoinInviteScreen({super.key, this.code, this.community = false});
  final String? code;
  final bool community;

  @override
  ConsumerState<JoinInviteScreen> createState() => _JoinInviteScreenState();
}

class _JoinInviteScreenState extends ConsumerState<JoinInviteScreen> {
  late final HimeCore core = ref.read(coreProvider);
  final _input = TextEditingController();
  Map<String, dynamic>? preview;
  bool isCommunity = false;
  bool loading = false;
  bool joining = false;
  String? message;

  @override
  void initState() {
    super.initState();
    if (widget.code != null) {
      _input.text = widget.code!;
      isCommunity = widget.community;
      _preview();
    }
  }

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _preview() async {
    final code = parseInviteCode(_input.text);
    if (code == null) {
      setState(() => message = 'Paste an invite link or enter a code');
      return;
    }
    final uri = Uri.tryParse(_input.text.trim());
    if (uri?.queryParameters['c'] == '1') isCommunity = true;
    setState(() {
      loading = true;
      message = null;
      preview = null;
    });
    try {
      Map<String, dynamic>? res;
      if (!isCommunity) {
        final g = await core.sb.rpc('preview_group_invite', params: {'p_code': code});
        if (g != null) res = Map<String, dynamic>.from(g as Map);
      }
      if (res == null) {
        final c = await core.sb.rpc('preview_community_invite', params: {'p_code': code});
        if (c != null) {
          res = Map<String, dynamic>.from(c as Map);
          isCommunity = true;
        }
      }
      setState(() {
        preview = res;
        message = res == null ? 'This invite link is invalid or was reset.' : null;
      });
    } catch (e) {
      setState(() => message = friendlyError(e));
    }
    if (mounted) setState(() => loading = false);
  }

  Future<void> _join() async {
    final code = parseInviteCode(_input.text);
    if (code == null || preview == null) return;
    setState(() => joining = true);
    try {
      if (isCommunity) {
        final id = await core.sb.rpc('join_community_by_invite', params: {'p_code': code}) as String;
        unawaited(core.chatList.refresh());
        if (mounted) context.pushReplacement('/community/$id');
      } else {
        final id = await core.sb.rpc('join_group_by_invite', params: {'p_code': code}) as String;
        await core.chatList.refresh();
        if (mounted) context.pushReplacement('/chat/$id');
      }
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => joining = false);
  }

  @override
  Widget build(BuildContext context) {
    final p = preview;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Join with invite'),
        leading: IconButton(
          icon: const Icon(Icons.close_rounded),
          onPressed: () => context.canPop() ? context.pop() : context.go('/chats'),
        ),
      ),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        HimeField(
          controller: _input,
          label: 'Invite link or code',
          hint: 'Paste the link you received',
          suffix: IconButton(icon: const Icon(Icons.arrow_forward_rounded), onPressed: loading ? null : _preview),
          onSubmitted: (_) => _preview(),
        ),
        const SizedBox(height: 20),
        if (loading) const CenteredLoader(),
        if (message != null) Text(message!, textAlign: TextAlign.center, style: TextStyle(color: context.colors.error)),
        if (p != null)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(children: [
                HimeAvatar(name: p['name'] as String? ?? '', size: 84, icon: isCommunity ? Icons.groups_2_rounded : Icons.groups_rounded),
                const SizedBox(height: 12),
                Text(p['name'] as String? ?? '', style: context.text.titleLarge, textAlign: TextAlign.center),
                const SizedBox(height: 4),
                Text('${isCommunity ? 'Community' : 'Group'} · ${p['member_count']} members',
                    style: context.text.bodyMedium?.copyWith(color: context.palette.muted)),
                if ((p['description'] as String? ?? '').isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(p['description'] as String, textAlign: TextAlign.center),
                ],
                const SizedBox(height: 20),
                PrimaryButton(
                  label: p['is_member'] == true ? 'Open' : 'Join ${isCommunity ? 'community' : 'group'}',
                  loading: joining,
                  onPressed: joining ? null : _join,
                ),
              ]),
            ),
          ),
      ]),
    );
  }
}
