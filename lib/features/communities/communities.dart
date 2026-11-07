import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import '../../services/session.dart';
import '../chats/extra_screens.dart';
import '../groups/groups.dart';

class CommunitiesScreen extends ConsumerStatefulWidget {
  const CommunitiesScreen({super.key});

  @override
  ConsumerState<CommunitiesScreen> createState() => _CommunitiesScreenState();
}

class _CommunitiesScreenState extends ConsumerState<CommunitiesScreen> {
  late final HimeCore core = ref.read(coreProvider);
  List<Map<String, dynamic>>? list;
  Object? error;
  StreamSubscription<Map<String, dynamic>>? _live;
  Timer? _reload;

  @override
  void initState() {
    super.initState();
    _load();
    // Joining, leaving or being added to community groups shows up live.
    _live = core.realtime.conversations.listen((_) {
      _reload?.cancel();
      _reload = Timer(const Duration(milliseconds: 800), _load);
    });
  }

  @override
  void dispose() {
    _reload?.cancel();
    _live?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final rows = (await core.sb.rpc('get_my_communities') as List<dynamic>).cast<Map<String, dynamic>>();
      if (mounted) {
        setState(() {
          list = rows;
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final items = list;
    return Scaffold(
      appBar: AppBar(title: const Text('Communities'), actions: [
        IconButton(tooltip: 'Join with code', icon: const Icon(Icons.qr_code_scanner_rounded), onPressed: () => context.push('/join')),
      ]),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/community/new').then((_) => _load()),
        icon: const Icon(Icons.add_rounded),
        label: const Text('New community'),
      ),
      body: error != null && items == null
          ? ErrorState(error: error!, onRetry: _load)
          : items == null
              ? const ListSkeleton(count: 5)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: items.isEmpty
                      ? ListView(children: const [
                          SizedBox(height: 60),
                          EmptyState(
                            icon: Icons.groups_2_rounded,
                            title: 'Stay connected with a community',
                            message: 'Communities bring related groups together under one roof, with an announcement group to reach everyone.',
                          ),
                        ])
                      : ListView.builder(
                          padding: const EdgeInsets.only(bottom: 96),
                          itemCount: items.length,
                          itemBuilder: (context, i) {
                            final c = items[i];
                            return ListTile(
                              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                              leading: HimeAvatar(
                                name: c['name'] as String? ?? '',
                                path: c['avatar_path'] as String?,
                                version: (c['avatar_version'] as num?)?.toInt() ?? 0,
                                size: 52,
                                icon: Icons.groups_2_rounded,
                              ),
                              title: Text(c['name'] as String? ?? '', style: context.text.titleMedium),
                              subtitle: Text('${c['member_count']} members · ${c['group_count']} groups'),
                              trailing: const Icon(Icons.chevron_right_rounded),
                              onTap: () => context.push('/community/${c['id']}').then((_) => _load()),
                            );
                          },
                        ),
                ),
    );
  }
}

class CreateCommunityScreen extends ConsumerStatefulWidget {
  const CreateCommunityScreen({super.key});

  @override
  ConsumerState<CreateCommunityScreen> createState() => _CreateCommunityScreenState();
}

class _CreateCommunityScreenState extends ConsumerState<CreateCommunityScreen> {
  late final HimeCore core = ref.read(coreProvider);
  final _name = TextEditingController();
  final _desc = TextEditingController();
  bool busy = false;

  @override
  void dispose() {
    _name.dispose();
    _desc.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    if (_name.text.trim().isEmpty) {
      toast(context, 'Give your community a name');
      return;
    }
    setState(() => busy = true);
    try {
      final res = Map<String, dynamic>.from(
          await core.sb.rpc('create_community', params: {'p_name': _name.text.trim(), 'p_description': _desc.text.trim()}) as Map);
      unawaited(core.chatList.refresh());
      if (mounted) context.pushReplacement('/community/${res['community_id']}');
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => busy = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New community')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        const Center(
          child: CircleAvatar(radius: 44, backgroundColor: HimeColors.yellow, child: Icon(Icons.groups_2_rounded, size: 44, color: HimeColors.ink)),
        ),
        const SizedBox(height: 16),
        Text('Create a new community', textAlign: TextAlign.center, style: context.text.titleLarge),
        const SizedBox(height: 6),
        Text('Bring together a neighbourhood, school, club or team. Every community gets an announcement group for updates.',
            textAlign: TextAlign.center, style: context.text.bodyMedium?.copyWith(color: context.palette.muted)),
        const SizedBox(height: 24),
        HimeField(controller: _name, label: 'Community name', maxLength: 64, textCapitalization: TextCapitalization.words),
        const SizedBox(height: 12),
        HimeField(controller: _desc, label: 'Description', maxLength: 512, maxLines: 4, textCapitalization: TextCapitalization.sentences),
        const SizedBox(height: 24),
        PrimaryButton(label: 'Create community', loading: busy, onPressed: busy ? null : _create),
      ]),
    );
  }
}

class CommunityScreen extends ConsumerStatefulWidget {
  const CommunityScreen({super.key, required this.communityId});
  final String communityId;

  @override
  ConsumerState<CommunityScreen> createState() => _CommunityScreenState();
}

class _CommunityScreenState extends ConsumerState<CommunityScreen> {
  late final HimeCore core = ref.read(coreProvider);
  Map<String, dynamic>? data;
  Object? error;
  StreamSubscription<Map<String, dynamic>>? _live;
  Timer? _reload;

  @override
  void initState() {
    super.initState();
    _load();
    _live = core.realtime.conversations.listen((_) {
      _reload?.cancel();
      _reload = Timer(const Duration(milliseconds: 800), _load);
    });
  }

  @override
  void dispose() {
    _reload?.cancel();
    _live?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final res = await core.sb.rpc('get_community', params: {'p_community_id': widget.communityId});
      if (res == null) throw StateError('You are not a member of this community.');
      if (mounted) {
        setState(() {
          data = Map<String, dynamic>.from(res as Map);
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  bool get isAdmin => data?['role'] == 'owner' || data?['role'] == 'admin';

  Future<void> _openGroup(Map<String, dynamic> g) async {
    final id = g['conversation_id'] as String;
    if (g['is_member'] == true) {
      context.push('/chat/$id');
      return;
    }
    final ok = await confirm(context, title: 'Join "${g['name']}"?', confirmLabel: 'Join');
    if (!ok || !mounted) return;
    final joined = await guard(context, () async {
      await core.sb.rpc('join_community_group', params: {'p_conversation_id': id});
      await core.chatList.refresh();
    });
    if (joined && mounted) {
      context.push('/chat/$id');
      unawaited(_load());
    }
  }

  Future<void> _invite() async {
    try {
      final code = await core.sb.rpc('get_community_invite', params: {'p_community_id': widget.communityId, 'p_reset': false}) as String;
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute<void>(
        builder: (_) => Scaffold(
          appBar: AppBar(title: const Text('Invite to community')),
          body: InviteCard(
            title: data?['name'] as String? ?? 'Community',
            subtitle: 'People who join with this link become community members and can join its groups.',
            code: code,
            link: inviteLink(code, community: true),
          ),
        ),
      ));
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
  }

  Future<void> _edit() async {
    final d = data;
    if (d == null) return;
    await showActionSheet(context, title: 'Edit community', actions: [
      SheetAction(Icons.edit_rounded, 'Change name', () async {
        final v = await promptText(context, title: 'Community name', initial: d['name'] as String?, maxLength: 64);
        if (v == null || v.isEmpty || !mounted) return;
        await guard(context, () => core.sb.rpc('update_community', params: {'p_community_id': widget.communityId, 'p_name': v}));
        await _load();
      }),
      SheetAction(Icons.notes_rounded, 'Change description', () async {
        final v = await promptText(context, title: 'Description', initial: d['description'] as String?, maxLength: 512, maxLines: 4);
        if (v == null || !mounted) return;
        await guard(context, () => core.sb.rpc('update_community', params: {'p_community_id': widget.communityId, 'p_description': v}));
        await _load();
      }),
      SheetAction(Icons.photo_camera_rounded, 'Change photo', () async {
        await guard(context, () async {
          final path = await uploadAvatar(core, 'communities/${widget.communityId}');
          if (path == null) return;
          await core.sb.rpc('update_community', params: {'p_community_id': widget.communityId, 'p_avatar_path': path});
        });
        await _load();
      }),
    ]);
  }

  Future<void> _leave() async {
    final ok = await confirm(context,
        title: 'Leave community?',
        message: 'You\'ll stay in any groups you joined, but leave the announcement group.',
        confirmLabel: 'Leave',
        danger: true);
    if (!ok || !mounted) return;
    final done = await guard(context, () async {
      final ann = data?['announcement_conversation_id'] as String?;
      if (ann != null) {
        await core.sb.from('conversation_members').delete().eq('conversation_id', ann).eq('user_id', core.userId);
      }
      await core.sb.from('community_members').delete().eq('community_id', widget.communityId).eq('user_id', core.userId);
      await core.chatList.refresh();
    });
    if (done && mounted) context.pop();
  }

  @override
  Widget build(BuildContext context) {
    final d = data;
    final groups = ((d?['groups'] as List?) ?? const []).cast<Map<String, dynamic>>();
    return Scaffold(
      appBar: AppBar(title: Text(d?['name'] as String? ?? 'Community'), actions: [
        if (isAdmin) IconButton(tooltip: 'Edit', icon: const Icon(Icons.edit_outlined), onPressed: _edit),
        PopupMenuButton<String>(
          onSelected: (v) {
            if (v == 'invite') _invite();
            if (v == 'leave') _leave();
          },
          itemBuilder: (_) => [
            if (isAdmin) const PopupMenuItem(value: 'invite', child: Text('Invite members')),
            if (d?['role'] != 'owner') const PopupMenuItem(value: 'leave', child: Text('Leave community')),
          ],
        ),
      ]),
      floatingActionButton: isAdmin
          ? FloatingActionButton.extended(
              onPressed: () => context.push('/new-group?community=${widget.communityId}').then((_) => _load()),
              icon: const Icon(Icons.group_add_rounded),
              label: const Text('New group'),
            )
          : null,
      body: error != null && d == null
          ? ErrorState(error: error!, onRetry: _load)
          : d == null
              ? const CenteredLoader()
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.only(bottom: 96), children: [
                    const SizedBox(height: 16),
                    Center(
                      child: HimeAvatar(
                        name: d['name'] as String? ?? '',
                        path: d['avatar_path'] as String?,
                        version: (d['avatar_version'] as num?)?.toInt() ?? 0,
                        size: 96,
                        icon: Icons.groups_2_rounded,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(d['name'] as String? ?? '', textAlign: TextAlign.center, style: context.text.headlineSmall),
                    Text('Community · ${d['member_count']} members',
                        textAlign: TextAlign.center, style: context.text.bodyMedium?.copyWith(color: context.palette.muted)),
                    if ((d['description'] as String? ?? '').isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(32, 10, 32, 0),
                        child: Text(d['description'] as String, textAlign: TextAlign.center),
                      ),
                    if (isAdmin)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                        child: OutlinedButton.icon(onPressed: _invite, icon: const Icon(Icons.person_add_alt_rounded), label: const Text('Invite members')),
                      ),
                    SettingsGroup(title: 'Groups', children: [
                      for (final g in groups)
                        ListTile(
                          leading: HimeAvatar(
                            name: g['name'] as String? ?? '',
                            path: g['avatar_path'] as String?,
                            version: (g['avatar_version'] as num?)?.toInt() ?? 0,
                            size: 44,
                            icon: g['is_announcement'] == true ? Icons.campaign_rounded : Icons.groups_rounded,
                          ),
                          title: Text(g['is_announcement'] == true ? 'Announcements' : (g['name'] as String? ?? '')),
                          subtitle: Text(g['is_member'] == true ? '${g['member_count']} members' : 'Tap to join · ${g['member_count']} members'),
                          trailing: g['is_member'] == true ? const Icon(Icons.chevron_right_rounded) : const Icon(Icons.add_circle_outline_rounded),
                          onTap: () => _openGroup(g),
                        ),
                    ]),
                  ]),
                ),
    );
  }
}
