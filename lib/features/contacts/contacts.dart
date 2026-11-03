import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_contacts/flutter_contacts.dart' hide Phone;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import '../../services/session.dart';
import '../chats/models.dart';

/// Contacts live on the server only as "this account saved that account";
/// phone numbers never leave the device, only their SHA-256 hashes are
/// compared (and only for people who chose to be discoverable by phone).
class ContactsRepo {
  ContactsRepo(this.core);
  final HimeCore core;

  Future<List<Profile>> profiles(List<String> ids) async {
    if (ids.isEmpty) return [];
    final rows = (await core.sb.rpc('get_profiles', params: {'p_ids': ids}) as List<dynamic>).cast<Map<String, dynamic>>();
    final list = rows.map(Profile.fromJson).toList();
    for (final p in list) {
      core.profiles.put(p);
    }
    list.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return list;
  }

  Future<List<Profile>> myContacts() async {
    final rows = await core.sb.from('user_contacts').select('contact_id').limit(5000);
    return profiles(rows.map((r) => r['contact_id'] as String).toList());
  }

  Future<List<Profile>> search(String query) async {
    final q = query.trim();
    if (q.replaceAll('@', '').length < 2) return [];
    final rows = (await core.sb.rpc('search_users', params: {'p_query': q, 'p_limit': 30}) as List<dynamic>)
        .cast<Map<String, dynamic>>();
    return rows.map(Profile.fromJson).toList();
  }

  Future<void> add(String userId) => core.sb
      .from('user_contacts')
      .upsert({'owner_id': core.userId, 'contact_id': userId}, onConflict: 'owner_id,contact_id', ignoreDuplicates: true);

  Future<void> remove(String userId) =>
      core.sb.from('user_contacts').delete().eq('owner_id', core.userId).eq('contact_id', userId);

  Future<List<Profile>> blocked() async {
    final rows = await core.sb.from('user_blocks').select('blocked_id').limit(5000);
    return profiles(rows.map((r) => r['blocked_id'] as String).toList());
  }

  /// Matches the phone book against Hime accounts. Returns matched profiles
  /// (which are also saved as contacts). Throws [StateError] without permission.
  Future<List<Profile>> syncPhoneBook({String defaultDial = '+91'}) async {
    if (!await FlutterContacts.requestPermission(readonly: true)) {
      throw StateError('Allow contacts access to find friends on Hime.');
    }
    final book = await FlutterContacts.getContacts(withProperties: true);
    final hashes = <String>{};
    for (final c in book) {
      for (final ph in c.phones) {
        final e164 = Phone.toE164(ph.number, defaultDial);
        if (e164 != null) hashes.add(Phone.hash(e164));
      }
    }
    final list = hashes.toList();
    final found = <String, Profile>{};
    for (var i = 0; i < list.length; i += 1000) {
      final chunk = list.sublist(i, (i + 1000).clamp(0, list.length));
      final rows = (await core.sb.rpc('match_contacts', params: {'p_hashes': chunk}) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      for (final r in rows) {
        final p = Profile.fromJson({...r, 'is_contact': true});
        found[p.id] = p;
      }
    }
    if (found.isNotEmpty) {
      await core.sb.from('user_contacts').upsert(
            [for (final id in found.keys) {'owner_id': core.userId, 'contact_id': id}],
            onConflict: 'owner_id,contact_id',
            ignoreDuplicates: true,
          );
    }
    return found.values.toList();
  }
}

/// Opens (or creates) the one-to-one chat with [userId].
Future<void> openDirectChat(BuildContext context, HimeCore core, String userId, {bool replace = false}) async {
  try {
    final id = await core.sb.rpc('get_or_create_direct', params: {'p_other': userId}) as String;
    unawaited(core.chatList.refresh());
    if (!context.mounted) return;
    if (replace) {
      context.pushReplacement('/chat/$id');
    } else {
      context.push('/chat/$id');
    }
  } catch (e) {
    if (context.mounted) toast(context, friendlyError(e));
  }
}

/// Search + contacts list used by new chat, new group, add members, etc.
class PeoplePicker extends StatefulWidget {
  const PeoplePicker({
    super.key,
    required this.core,
    this.multi = false,
    this.exclude = const {},
    this.initial = const [],
    this.onPick,
    this.onSelectionChanged,
    this.header,
  });

  final HimeCore core;
  final bool multi;
  final Set<String> exclude;
  final List<Profile> initial;
  final ValueChanged<Profile>? onPick;
  final ValueChanged<List<Profile>>? onSelectionChanged;
  final List<Widget>? header;

  @override
  State<PeoplePicker> createState() => PeoplePickerState();
}

class PeoplePickerState extends State<PeoplePicker> {
  late final repo = ContactsRepo(widget.core);
  final _query = TextEditingController();
  final _debounce = Debouncer(const Duration(milliseconds: 350));
  List<Profile> _contacts = [];
  List<Profile> _results = [];
  bool _loading = true;
  bool _searching = false;
  bool _syncing = false;
  late final List<Profile> selected = [...widget.initial];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final list = await repo.myContacts();
      if (mounted) setState(() => _contacts = list);
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => _loading = false);
  }

  void _onQuery(String q) {
    setState(() {});
    if (q.trim().length < 2) {
      setState(() => _results = []);
      return;
    }
    _debounce(() async {
      setState(() => _searching = true);
      try {
        final r = await repo.search(q);
        if (mounted && _query.text == q) setState(() => _results = r);
      } catch (_) {}
      if (mounted) setState(() => _searching = false);
    });
  }

  Future<void> _sync() async {
    setState(() => _syncing = true);
    try {
      final found = await repo.syncPhoneBook();
      await _load();
      if (mounted) toast(context, found.isEmpty ? 'None of your contacts are on Hime yet' : 'Found ${found.length} contact(s) on Hime');
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => _syncing = false);
  }

  void _tap(Profile p) {
    if (!widget.multi) {
      widget.onPick?.call(p);
      return;
    }
    setState(() {
      final i = selected.indexWhere((s) => s.id == p.id);
      if (i >= 0) {
        selected.removeAt(i);
      } else {
        selected.add(p);
      }
    });
    widget.onSelectionChanged?.call(List.unmodifiable(selected));
  }

  @override
  void dispose() {
    _query.dispose();
    _debounce.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final q = _query.text.trim().toLowerCase();
    final contacts = _contacts
        .where((c) => !widget.exclude.contains(c.id))
        .where((c) => q.isEmpty || c.name.toLowerCase().contains(q) || (c.username ?? '').contains(q))
        .toList();
    final contactIds = contacts.map((c) => c.id).toSet();
    final others = _results.where((r) => !widget.exclude.contains(r.id) && !contactIds.contains(r.id)).toList();

    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
        child: TextField(
          controller: _query,
          onChanged: _onQuery,
          decoration: InputDecoration(
            prefixIcon: const Icon(Icons.search_rounded),
            hintText: 'Search name or @username',
            suffixIcon: _searching
                ? const Padding(padding: EdgeInsets.all(14), child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)))
                : null,
          ),
        ),
      ),
      if (widget.multi && selected.isNotEmpty)
        SizedBox(
          height: 86,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            children: [
              for (final s in selected)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                  child: GestureDetector(
                    onTap: () => _tap(s),
                    child: Column(children: [
                      Stack(children: [
                        HimeAvatar(name: s.name, path: s.avatarPath, version: s.avatarVersion, size: 52),
                        Positioned(
                          right: 0,
                          bottom: 0,
                          child: Container(
                            decoration: BoxDecoration(color: context.colors.surface, shape: BoxShape.circle),
                            child: const Icon(Icons.cancel_rounded, size: 18),
                          ),
                        ),
                      ]),
                      const SizedBox(height: 4),
                      SizedBox(
                        width: 60,
                        child: Text(s.name.split(' ').first, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center, style: context.text.labelSmall),
                      ),
                    ]),
                  ),
                ),
            ],
          ),
        ),
      Expanded(
        child: _loading
            ? const ListSkeleton()
            : ListView(children: [
                ...?widget.header,
                if (contacts.isNotEmpty) _SectionLabel(q.isEmpty ? 'Contacts on Hime' : 'Contacts'),
                for (final c in contacts) _personTile(c),
                if (others.isNotEmpty) const _SectionLabel('Other people on Hime'),
                for (final c in others) _personTile(c),
                if (contacts.isEmpty && others.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(children: [
                      Icon(Icons.person_search_rounded, size: 48, color: context.palette.muted),
                      const SizedBox(height: 12),
                      Text(
                        q.length >= 2 ? 'No one found for "$q"' : 'Search by name or @username, or find friends from your phone contacts.',
                        textAlign: TextAlign.center,
                        style: context.text.bodyMedium?.copyWith(color: context.palette.muted),
                      ),
                    ]),
                  ),
                if (q.isEmpty)
                  ListTile(
                    leading: CircleAvatar(
                      backgroundColor: HimeColors.yellowSoft,
                      child: _syncing
                          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.sync_rounded, color: HimeColors.ink),
                    ),
                    title: const Text('Find friends from phone contacts'),
                    subtitle: const Text('Numbers are hashed on your phone before matching'),
                    onTap: _syncing ? null : _sync,
                  ),
                const SizedBox(height: 24),
              ]),
      ),
    ]);
  }

  Widget _personTile(Profile p) {
    final isSelected = selected.any((s) => s.id == p.id);
    return ListTile(
      leading: HimeAvatar(name: p.name, path: p.avatarPath, version: p.avatarVersion, size: 44),
      title: Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: p.username == null ? null : Text('@${p.username}'),
      trailing: widget.multi
          ? AnimatedSwitcher(
              duration: const Duration(milliseconds: 150),
              child: Icon(
                isSelected ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                key: ValueKey(isSelected),
                color: isSelected ? HimeColors.yellowDeep : context.palette.muted,
              ),
            )
          : null,
      onTap: () => _tap(p),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 6),
        child: Text(text, style: context.text.labelLarge?.copyWith(color: context.palette.muted, fontWeight: FontWeight.w600)),
      );
}

class ContactsScreen extends ConsumerStatefulWidget {
  const ContactsScreen({super.key});

  @override
  ConsumerState<ContactsScreen> createState() => _ContactsScreenState();
}

class _ContactsScreenState extends ConsumerState<ContactsScreen> {
  late final core = ref.read(coreProvider);
  late final repo = ContactsRepo(core);
  Future<List<Profile>>? _future;
  bool _syncing = false;

  @override
  void initState() {
    super.initState();
    _future = repo.myContacts();
  }

  Future<void> _sync() async {
    setState(() => _syncing = true);
    try {
      final found = await repo.syncPhoneBook();
      if (mounted) toast(context, found.isEmpty ? 'None of your contacts are on Hime yet' : 'Found ${found.length} contact(s) on Hime');
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) {
      setState(() {
        _syncing = false;
        _future = repo.myContacts();
      });
    }
  }

  Future<void> _add() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SizedBox(
        height: MediaQuery.of(ctx).size.height * 0.85,
        child: PeoplePicker(
          core: core,
          onPick: (p) async {
            Navigator.pop(ctx);
            await guard(context, () => repo.add(p.id), success: '${p.name} added to contacts');
            if (mounted) setState(() => _future = repo.myContacts());
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Contacts'), actions: [
        IconButton(
          tooltip: 'Sync phone contacts',
          onPressed: _syncing ? null : _sync,
          icon: _syncing
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.sync_rounded),
        ),
      ]),
      floatingActionButton: FloatingActionButton(onPressed: _add, child: const Icon(Icons.person_add_alt_1_rounded)),
      body: FutureBuilder<List<Profile>>(
        future: _future,
        builder: (context, snap) {
          if (snap.hasError) return ErrorState(error: snap.error!, onRetry: () => setState(() => _future = repo.myContacts()));
          if (!snap.hasData) return const ListSkeleton();
          final list = snap.data!;
          if (list.isEmpty) {
            return EmptyState(
              icon: Icons.contacts_rounded,
              title: 'No contacts yet',
              message: 'Add people by @username or find friends from your phone contacts.',
              action: PrimaryButton(label: 'Find friends', icon: Icons.sync_rounded, onPressed: _sync, loading: _syncing),
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              final f = repo.myContacts();
              setState(() => _future = f);
              await f;
            },
            child: ListView.builder(
              itemCount: list.length,
              itemBuilder: (context, i) {
                final p = list[i];
                return ListTile(
                  leading: HimeAvatar(name: p.name, path: p.avatarPath, version: p.avatarVersion, size: 44),
                  title: Text(p.name),
                  subtitle: Text(p.about?.isNotEmpty == true ? p.about! : (p.username == null ? '' : '@${p.username}'),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                  onTap: () => context.push('/user/${p.id}'),
                  trailing: PopupMenuButton<String>(
                    onSelected: (v) async {
                      if (v == 'chat') await openDirectChat(context, core, p.id);
                      if (v == 'remove') {
                        await guard(context, () => repo.remove(p.id));
                        if (mounted) setState(() => _future = repo.myContacts());
                      }
                    },
                    itemBuilder: (_) => const [
                      PopupMenuItem(value: 'chat', child: Text('Message')),
                      PopupMenuItem(value: 'remove', child: Text('Remove contact')),
                    ],
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class BlockedScreen extends ConsumerStatefulWidget {
  const BlockedScreen({super.key});

  @override
  ConsumerState<BlockedScreen> createState() => _BlockedScreenState();
}

class _BlockedScreenState extends ConsumerState<BlockedScreen> {
  late final core = ref.read(coreProvider);
  late final repo = ContactsRepo(core);
  late Future<List<Profile>> _future = repo.blocked();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Blocked contacts')),
      body: FutureBuilder<List<Profile>>(
        future: _future,
        builder: (context, snap) {
          if (snap.hasError) return ErrorState(error: snap.error!, onRetry: () => setState(() => _future = repo.blocked()));
          if (!snap.hasData) return const ListSkeleton(count: 4);
          final list = snap.data!;
          if (list.isEmpty) {
            return const EmptyState(
              icon: Icons.block_rounded,
              title: 'No blocked contacts',
              message: 'Blocked people can\'t message or call you, and won\'t see your last seen, photo or status.',
            );
          }
          return ListView(children: [
            for (final p in list)
              ListTile(
                leading: HimeAvatar(name: p.name, path: p.avatarPath, version: p.avatarVersion, size: 44),
                title: Text(p.name),
                subtitle: p.username == null ? null : Text('@${p.username}'),
                trailing: TextButton(
                  onPressed: () async {
                    await guard(context, () => core.sb.from('user_blocks').delete().eq('blocker_id', core.userId).eq('blocked_id', p.id),
                        success: '${p.name} unblocked');
                    unawaited(core.chatList.refresh());
                    if (mounted) setState(() => _future = repo.blocked());
                  },
                  child: const Text('Unblock'),
                ),
              ),
          ]);
        },
      ),
    );
  }
}
