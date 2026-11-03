import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import '../../services/session.dart';
import '../chats/models.dart';
import '../contacts/contacts.dart';

/// Global search: chats, people and messages. Message search runs over the
/// decrypted copies stored on this phone only.
class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  late final HimeCore core = ref.read(coreProvider);
  late final repo = ContactsRepo(core);
  final _q = TextEditingController();
  final _debounce = Debouncer(const Duration(milliseconds: 300));
  List<ChatSummary> chats = [];
  List<Profile> people = [];
  List<ChatMessage> messages = [];
  String filter = 'all';
  bool busy = false;

  @override
  void dispose() {
    _q.dispose();
    _debounce.dispose();
    super.dispose();
  }

  void _search(String v) {
    final q = v.trim();
    if (q.isEmpty) {
      setState(() {
        chats = [];
        people = [];
        messages = [];
      });
      return;
    }
    _debounce(() async {
      setState(() => busy = true);
      final lower = q.toLowerCase();
      final c = core.chatList.chats.where((x) => x.title.toLowerCase().contains(lower)).toList();
      final m = await core.chats.search(q);
      List<Profile> p = [];
      try {
        p = await repo.search(q);
      } catch (_) {}
      if (!mounted || _q.text.trim() != q) return;
      setState(() {
        chats = c;
        messages = m;
        people = p;
        busy = false;
      });
    });
  }

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 6),
        child: Text(t, style: context.text.labelLarge?.copyWith(color: context.palette.muted, fontWeight: FontWeight.w600)),
      );

  @override
  Widget build(BuildContext context) {
    final q = _q.text.trim();
    final showChats = filter == 'all' || filter == 'chats';
    final showPeople = filter == 'all' || filter == 'people';
    final showMessages = filter == 'all' || filter == 'messages';
    final nothing = q.isNotEmpty && !busy && chats.isEmpty && people.isEmpty && messages.isEmpty;
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: TextField(
          controller: _q,
          autofocus: true,
          onChanged: _search,
          textInputAction: TextInputAction.search,
          decoration: const InputDecoration(
            hintText: 'Search chats, people and messages',
            filled: false,
            border: InputBorder.none,
            enabledBorder: InputBorder.none,
            focusedBorder: InputBorder.none,
          ),
        ),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: SizedBox(
            height: 48,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
              for (final (key, label) in [('all', 'All'), ('chats', 'Chats'), ('people', 'People'), ('messages', 'Messages')])
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                  child: ChoiceChip(label: Text(label), selected: filter == key, onSelected: (_) => setState(() => filter = key)),
                ),
            ]),
          ),
        ),
      ),
      body: q.isEmpty
          ? const EmptyState(
              icon: Icons.search_rounded,
              title: 'Search Hime',
              message: 'Find chats, people by @username, and messages. Message search happens on your phone.',
            )
          : nothing
              ? EmptyState(icon: Icons.search_off_rounded, title: 'No results', message: 'Nothing matches "$q".')
              : ListView(children: [
                  if (busy) const LinearProgressIndicator(minHeight: 2),
                  if (showChats && chats.isNotEmpty) ...[
                    _label('Chats'),
                    for (final c in chats)
                      ListTile(
                        leading: HimeAvatar(name: c.title, path: c.avatarPath, version: c.avatarVersion, size: 44, icon: c.isGroup ? Icons.groups_rounded : null),
                        title: Text(c.title),
                        subtitle: c.lastPreview == null ? null : Text(c.lastPreview!, maxLines: 1, overflow: TextOverflow.ellipsis),
                        onTap: () => context.push('/chat/${c.id}'),
                      ),
                  ],
                  if (showPeople && people.isNotEmpty) ...[
                    _label('People'),
                    for (final p in people)
                      ListTile(
                        leading: HimeAvatar(name: p.name, path: p.avatarPath, version: p.avatarVersion, size: 44),
                        title: Text(p.name),
                        subtitle: p.username == null ? null : Text('@${p.username}'),
                        trailing: p.isContact ? const Icon(Icons.contacts_rounded, size: 18) : null,
                        onTap: () => context.push('/user/${p.id}'),
                      ),
                  ],
                  if (showMessages && messages.isNotEmpty) ...[
                    _label('Messages'),
                    for (final m in messages)
                      ListTile(
                        leading: const CircleAvatar(backgroundColor: HimeColors.yellowSoft, child: Icon(Icons.chat_bubble_outline_rounded, color: HimeColors.ink, size: 20)),
                        title: Text(core.chatList.byId(m.conversationId)?.title ?? core.profiles.nameOf(m.senderId)),
                        subtitle: Text('${m.senderId == core.userId ? 'You: ' : ''}${m.preview()}', maxLines: 2, overflow: TextOverflow.ellipsis),
                        trailing: Text(Fmt.chatTime(m.createdAt), style: context.text.labelSmall),
                        onTap: () => context.push('/chat/${m.conversationId}'),
                      ),
                  ],
                  const SizedBox(height: 24),
                ]),
    );
  }
}
