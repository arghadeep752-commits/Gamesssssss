import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../app.dart';
import '../../core/config.dart';
import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/core.dart';
import '../../services/notifications.dart';
import '../../services/session.dart';
import 'legal_texts.dart';

// ---------------------------------------------------------------- main tab

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionProvider);
    final me = session.profile;
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(padding: const EdgeInsets.only(bottom: 32), children: [
        InkWell(
          onTap: () => context.push('/profile/edit'),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
            child: Row(children: [
              HimeAvatar(name: me?.name ?? '', path: me?.avatarPath, version: me?.avatarVersion ?? 0, size: 64),
              const SizedBox(width: 16),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(me?.name ?? '', style: context.text.titleLarge, maxLines: 1, overflow: TextOverflow.ellipsis),
                  const SizedBox(height: 2),
                  Text(
                    (me?.about ?? '').isNotEmpty ? me!.about : (me?.username == null ? 'Set up your profile' : '@${me!.username}'),
                    style: context.text.bodyMedium?.copyWith(color: context.palette.muted),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ]),
              ),
              const Icon(Icons.chevron_right_rounded),
            ]),
          ),
        ),
        SettingsGroup(children: [
          SettingsTile(icon: Icons.key_rounded, title: 'Account', subtitle: 'Phone number, export, delete', onTap: () => context.push('/settings/account')),
          SettingsTile(icon: Icons.lock_outline_rounded, title: 'Privacy', subtitle: 'Last seen, photo, read receipts, blocked', onTap: () => context.push('/settings/privacy')),
          SettingsTile(icon: Icons.shield_outlined, title: 'Security', subtitle: 'Encryption, two-step verification', onTap: () => context.push('/settings/security')),
          SettingsTile(icon: Icons.devices_rounded, title: 'Linked devices', onTap: () => context.push('/settings/devices')),
        ]),
        SettingsGroup(children: [
          SettingsTile(icon: Icons.chat_bubble_outline_rounded, title: 'Chats', subtitle: 'Enter key, clear chats', onTap: () => context.push('/settings/chats')),
          SettingsTile(icon: Icons.notifications_none_rounded, title: 'Notifications', onTap: () => context.push('/settings/notifications')),
          SettingsTile(icon: Icons.palette_outlined, title: 'Appearance', subtitle: 'Theme', onTap: () => context.push('/settings/appearance')),
          SettingsTile(icon: Icons.data_usage_rounded, title: 'Storage and data', onTap: () => context.push('/settings/storage')),
          SettingsTile(icon: Icons.language_rounded, title: 'App language', subtitle: 'English', onTap: () => context.push('/settings/language')),
        ]),
        SettingsGroup(children: [
          SettingsTile(icon: Icons.star_outline_rounded, title: 'Starred messages', onTap: () => context.push('/starred')),
          SettingsTile(icon: Icons.contacts_outlined, title: 'Contacts', onTap: () => context.push('/contacts')),
          SettingsTile(
            icon: Icons.favorite_border_rounded,
            title: 'Invite a friend',
            onTap: () => SharePlus.instance.share(ShareParams(
                text: 'I\'m using Hime for private messages and calls. Join me! Find me as @${me?.username ?? ''} on Hime.')),
          ),
          SettingsTile(icon: Icons.help_outline_rounded, title: 'Help', onTap: () => context.push('/settings/help')),
          SettingsTile(icon: Icons.info_outline_rounded, title: 'About Hime', onTap: () => context.push('/settings/about')),
        ]),
        SettingsGroup(children: [
          SettingsTile(
            icon: Icons.logout_rounded,
            title: 'Sign out',
            danger: true,
            onTap: () async {
              final ok = await confirm(context,
                  title: 'Sign out?',
                  message: 'Messages stored on this phone will be removed. Your chats stay available on your other devices.',
                  confirmLabel: 'Sign out',
                  danger: true);
              if (ok) await session.signOut();
            },
          ),
        ]),
        const SizedBox(height: 8),
        Center(child: Text('Made with love in India 🇮🇳', style: context.text.labelMedium?.copyWith(color: context.palette.muted))),
      ]),
    );
  }
}

// ---------------------------------------------------------------- account

class AccountScreen extends ConsumerStatefulWidget {
  const AccountScreen({super.key});

  @override
  ConsumerState<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends ConsumerState<AccountScreen> {
  bool exporting = false;

  bool _realEmail(String? email) => (email ?? '').isNotEmpty && !isPlaceholderEmail(email);

  Future<void> _changePhone() async {
    final changed = await context.push<bool>('/settings/phone');
    if (changed == true && mounted) {
      await ref.read(sessionProvider).refreshProfile().catchError((_) {});
      if (mounted) setState(() {});
    }
  }

  Future<void> _changeEmail() async {
    final v = await promptText(context, title: 'New email address', hint: 'you@example.com', maxLength: 254);
    if (v == null || v.isEmpty || !mounted) return;
    final err = Validators.email(v);
    if (err != null) {
      toast(context, err);
      return;
    }
    await guard(context, () async {
      await Supabase.instance.client.auth.updateUser(UserAttributes(email: v), emailRedirectTo: AppConfig.instance.authRedirectUrl);
    }, success: 'Check both inboxes to confirm the change');
  }

  Future<void> _changePassword() async {
    final c1 = TextEditingController();
    final c2 = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Change password'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: c1, obscureText: true, decoration: const InputDecoration(labelText: 'New password')),
          const SizedBox(height: 12),
          TextField(controller: c2, obscureText: true, decoration: const InputDecoration(labelText: 'Repeat new password')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final err = Validators.password(c1.text);
    if (err != null) {
      toast(context, err);
      return;
    }
    if (c1.text != c2.text) {
      toast(context, 'Passwords don\'t match');
      return;
    }
    await guard(context, () => Supabase.instance.client.auth.updateUser(UserAttributes(password: c1.text)), success: 'Password changed');
  }

  Future<void> _export() async {
    final core = ref.read(coreProvider);
    setState(() => exporting = true);
    try {
      final server = await core.sb.rpc('export_my_data');
      final local = await core.db.recent(limit: 100000);
      final data = {
        'exported_at': DateTime.now().toUtc().toIso8601String(),
        'account': server,
        'messages_on_this_device': [
          for (final m in local)
            {
              'id': m.id,
              'conversation_id': m.conversationId,
              'sender_id': m.senderId,
              'kind': m.kind,
              'created_at': m.createdAt.toIso8601String(),
              'content': m.payload,
              if (m.system != null) 'event': m.system,
            },
        ],
      };
      final dir = await getTemporaryDirectory();
      final f = File(p.join(dir.path, 'hime-data-export.json'));
      await f.writeAsString(const JsonEncoder.withIndent('  ').convert(data));
      await SharePlus.instance.share(ShareParams(files: [XFile(f.path)], subject: 'My Hime data'));
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => exporting = false);
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(sessionProvider).user;
    return Scaffold(
      appBar: AppBar(title: const Text('Account')),
      body: ListView(children: [
        SettingsGroup(title: 'Sign-in', children: [
          // You sign in with your phone number (a 6-digit SMS code).
          if ((user?.phone ?? '').isNotEmpty)
            SettingsTile(
              icon: Icons.phone_outlined,
              title: 'Phone number',
              subtitle: prettyPhone(user!.phone!),
              trailing: const Text('Change'),
              onTap: _changePhone,
            )
          else
            SettingsTile(
              icon: Icons.phone_outlined,
              title: 'Add your phone number',
              subtitle: 'Sign in with it and let friends find you on Hime',
              onTap: _changePhone,
            ),
          // Older accounts that were created with an email keep seeing it.
          if (_realEmail(user?.email))
            SettingsTile(icon: Icons.mail_outline_rounded, title: 'Email', subtitle: user!.email, onTap: _changeEmail),
          if (_realEmail(user?.email)) SettingsTile(icon: Icons.password_rounded, title: 'Change password', onTap: _changePassword),
          SettingsTile(icon: Icons.verified_user_outlined, title: 'Two-step verification', onTap: () => context.push('/settings/two-step')),
        ]),
        SettingsGroup(title: 'Your data', children: [
          SettingsTile(
            icon: Icons.download_rounded,
            title: 'Export my data',
            subtitle: 'Your profile, settings, contacts, groups and the messages stored on this phone',
            trailing: exporting ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : null,
            onTap: exporting ? null : _export,
          ),
          SettingsTile(
            icon: Icons.logout_rounded,
            title: 'Sign out of all devices',
            onTap: () async {
              final ok = await confirm(context, title: 'Sign out everywhere?', confirmLabel: 'Sign out', danger: true);
              if (ok) await ref.read(sessionProvider).signOut(everywhere: true);
            },
          ),
          SettingsTile(
            icon: Icons.delete_forever_outlined,
            title: 'Delete my account',
            danger: true,
            onTap: () => context.push('/settings/delete-account'),
          ),
        ]),
      ]),
    );
  }
}

class DeleteAccountScreen extends ConsumerStatefulWidget {
  const DeleteAccountScreen({super.key});

  @override
  ConsumerState<DeleteAccountScreen> createState() => _DeleteAccountScreenState();
}

class _DeleteAccountScreenState extends ConsumerState<DeleteAccountScreen> {
  final _confirm = TextEditingController();
  bool busy = false;

  @override
  void dispose() {
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _delete() async {
    if (_confirm.text.trim() != 'DELETE') {
      toast(context, 'Type DELETE to confirm');
      return;
    }
    setState(() => busy = true);
    try {
      final res = await Supabase.instance.client.functions.invoke('delete-account', body: {'confirm': 'DELETE'});
      if (res.status >= 300) throw StateError('The server could not delete your account. Please try again.');
      await NotificationService.instance.unregisterPush();
      await Supabase.instance.client.auth.signOut(scope: SignOutScope.local);
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Delete account')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        Icon(Icons.warning_amber_rounded, size: 56, color: context.colors.error),
        const SizedBox(height: 12),
        Text('Deleting your account will:', style: context.text.titleMedium),
        const SizedBox(height: 8),
        for (final line in const [
          'Delete your profile, photo, username and settings',
          'Remove you from all groups and communities',
          'Delete files and status updates you uploaded',
          'Erase your encryption keys — messages sent to you can no longer be decrypted',
          'This cannot be undone',
        ])
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('•  '),
              Expanded(child: Text(line)),
            ]),
          ),
        const SizedBox(height: 20),
        HimeField(controller: _confirm, label: 'Type DELETE to confirm'),
        const SizedBox(height: 20),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: context.colors.error, foregroundColor: Colors.white, minimumSize: const Size.fromHeight(52)),
          onPressed: busy ? null : _delete,
          child: busy
              ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white))
              : const Text('Delete my account'),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- privacy

class PrivacyScreen extends ConsumerStatefulWidget {
  const PrivacyScreen({super.key});

  @override
  ConsumerState<PrivacyScreen> createState() => _PrivacyScreenState();
}

class _PrivacyScreenState extends ConsumerState<PrivacyScreen> {
  late final HimeCore core = ref.read(coreProvider);
  Map<String, dynamic>? s;
  Object? error;

  static const _labels = {
    'everyone': 'Everyone',
    'contacts': 'My contacts',
    'nobody': 'Nobody',
    'same_as_last_seen': 'Same as last seen',
    'contacts_except': 'My contacts except…',
    'only_share_with': 'Only share with…',
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final row = await core.sb.from('user_privacy_settings').select().eq('user_id', core.userId).maybeSingle();
      if (mounted) setState(() => s = row ?? {});
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  Future<void> _set(String key, Object value) async {
    final before = s?[key];
    setState(() => s = {...?s, key: value});
    final ok = await guard(context, () => core.sb.from('user_privacy_settings').update({key: value}).eq('user_id', core.userId));
    if (!ok && mounted) setState(() => s = {...?s, key: before});
  }

  Future<void> _choose(String key, String title, List<String> options) async {
    final current = s?[key] as String?;
    final v = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Padding(padding: const EdgeInsets.all(12), child: Text(title, style: ctx.text.titleMedium)),
          for (final o in options)
            ListTile(
              leading: Icon(o == current ? Icons.radio_button_checked_rounded : Icons.radio_button_unchecked_rounded,
                  color: o == current ? HimeColors.yellowDeep : null),
              title: Text(_labels[o] ?? o),
              onTap: () => Navigator.pop(ctx, o),
            ),
          const SizedBox(height: 8),
        ]),
      ),
    );
    if (v != null && v != current) await _set(key, v);
  }

  @override
  Widget build(BuildContext context) {
    final v = s;
    String label(String key) => _labels[v?[key]] ?? '—';
    return Scaffold(
      appBar: AppBar(title: const Text('Privacy')),
      body: error != null && v == null
          ? ErrorState(error: error!, onRetry: _load)
          : v == null
              ? const CenteredLoader()
              : ListView(children: [
                  SettingsGroup(title: 'Who can see my personal info', children: [
                    SettingsTile(
                        icon: Icons.access_time_rounded,
                        title: 'Last seen',
                        subtitle: label('last_seen'),
                        onTap: () => _choose('last_seen', 'Who can see my last seen', ['everyone', 'contacts', 'nobody'])),
                    SettingsTile(
                        icon: Icons.circle_outlined,
                        title: 'Online',
                        subtitle: label('online'),
                        onTap: () => _choose('online', 'Who can see when I\'m online', ['everyone', 'same_as_last_seen'])),
                    SettingsTile(
                        icon: Icons.account_circle_outlined,
                        title: 'Profile photo',
                        subtitle: label('profile_photo'),
                        onTap: () => _choose('profile_photo', 'Who can see my profile photo', ['everyone', 'contacts', 'nobody'])),
                    SettingsTile(
                        icon: Icons.info_outline_rounded,
                        title: 'About',
                        subtitle: label('about'),
                        onTap: () => _choose('about', 'Who can see my about', ['everyone', 'contacts', 'nobody'])),
                    SettingsTile(
                        icon: Icons.blur_circular_outlined,
                        title: 'Status',
                        subtitle: label('status_audience'),
                        onTap: () => context.push('/status/privacy').then((_) => _load())),
                  ]),
                  SettingsGroup(children: [
                    SwitchListTile(
                      secondary: const Icon(Icons.done_all_rounded),
                      title: const Text('Read receipts'),
                      subtitle: const Text('If turned off, you won\'t send or receive read receipts in one-to-one chats.'),
                      value: v['read_receipts'] != false,
                      onChanged: (x) => _set('read_receipts', x),
                    ),
                    SwitchListTile(
                      secondary: const Icon(Icons.phone_android_rounded),
                      title: const Text('Find me by phone number'),
                      subtitle: const Text('Let people who have your number in their contacts find you on Hime.'),
                      value: v['discoverable_by_phone'] != false,
                      onChanged: (x) => _set('discoverable_by_phone', x),
                    ),
                  ]),
                  SettingsGroup(title: 'Messaging and calls', children: [
                    SettingsTile(
                        icon: Icons.group_add_outlined,
                        title: 'Who can add me to groups',
                        subtitle: label('groups_add'),
                        onTap: () => _choose('groups_add', 'Who can add me to groups', ['everyone', 'contacts', 'nobody'])),
                    SettingsTile(
                        icon: Icons.call_outlined,
                        title: 'Who can call me',
                        subtitle: label('calls_from'),
                        onTap: () => _choose('calls_from', 'Who can call me', ['everyone', 'contacts'])),
                    SettingsTile(icon: Icons.block_rounded, title: 'Blocked contacts', onTap: () => context.push('/blocked')),
                  ]),
                ]),
    );
  }
}

// ---------------------------------------------------------------- security

class SecurityScreen extends ConsumerWidget {
  const SecurityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final core = ref.watch(coreProvider);
    final key = core.e2ee.publicKeyB64;
    final fingerprint = base64Decode(key).take(16).map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    final grouped = [for (var i = 0; i < fingerprint.length; i += 4) fingerprint.substring(i, i + 4)].join(' ');
    return Scaffold(
      appBar: AppBar(title: const Text('Security')),
      body: ListView(children: [
        const SizedBox(height: 16),
        const Center(
          child: CircleAvatar(radius: 40, backgroundColor: HimeColors.yellow, child: Icon(Icons.lock_rounded, size: 40, color: HimeColors.ink)),
        ),
        Padding(
          padding: const EdgeInsets.all(20),
          child: Column(children: [
            Text('Your chats and calls are private', style: context.text.titleLarge, textAlign: TextAlign.center),
            const SizedBox(height: 8),
            Text(
              'Messages, photos, videos, voice messages, documents and calls are end-to-end encrypted. They are encrypted on your phone with keys that never leave your devices, so not even Hime can read or listen to them.',
              textAlign: TextAlign.center,
              style: context.text.bodyMedium?.copyWith(color: context.palette.muted),
            ),
          ]),
        ),
        SettingsGroup(title: 'This device', children: [
          ListTile(
            leading: const Icon(Icons.fingerprint_rounded),
            title: const Text('Device key fingerprint'),
            subtitle: SelectableText(grouped, style: const TextStyle(fontFamily: 'monospace')),
          ),
        ]),
        SettingsGroup(children: [
          SettingsTile(icon: Icons.verified_user_outlined, title: 'Two-step verification', onTap: () => context.push('/settings/two-step')),
          SettingsTile(icon: Icons.devices_rounded, title: 'Linked devices', onTap: () => context.push('/settings/devices')),
          SettingsTile(icon: Icons.description_outlined, title: 'Privacy policy', onTap: () => context.push('/settings/legal/privacy')),
        ]),
        Padding(
          padding: const EdgeInsets.all(20),
          child: Text(
            'To verify a contact, open their chat → contact info → Encryption, and compare the security code together.',
            style: context.text.bodySmall?.copyWith(color: context.palette.muted),
          ),
        ),
      ]),
    );
  }
}

class TwoStepScreen extends ConsumerStatefulWidget {
  const TwoStepScreen({super.key});

  @override
  ConsumerState<TwoStepScreen> createState() => _TwoStepScreenState();
}

class _TwoStepScreenState extends ConsumerState<TwoStepScreen> {
  GoTrueMFAApi get mfa => Supabase.instance.client.auth.mfa;
  List<Factor>? factors;
  String? enrollId;
  String? enrollUri;
  String? enrollSecret;
  final _code = TextEditingController();
  bool busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final res = await mfa.listFactors();
      if (mounted) setState(() => factors = res.totp.where((f) => f.status == FactorStatus.verified).toList());
    } catch (e) {
      if (mounted) {
        setState(() => factors = []);
        toast(context, friendlyError(e));
      }
    }
  }

  Future<void> _start() async {
    setState(() => busy = true);
    try {
      final all = await mfa.listFactors();
      for (final f in all.all.where((f) => f.status != FactorStatus.verified)) {
        try {
          await mfa.unenroll(f.id);
        } catch (_) {}
      }
      final res = await mfa.enroll(factorType: FactorType.totp, issuer: 'Hime', friendlyName: 'Authenticator ${DateTime.now().millisecondsSinceEpoch}');
      setState(() {
        enrollId = res.id;
        enrollUri = res.totp?.uri;
        enrollSecret = res.totp?.secret;
      });
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => busy = false);
  }

  Future<void> _verify() async {
    final id = enrollId;
    if (id == null || _code.text.trim().length != 6) {
      toast(context, 'Enter the 6-digit code from your authenticator app');
      return;
    }
    setState(() => busy = true);
    try {
      await mfa.challengeAndVerify(factorId: id, code: _code.text.trim());
      _code.clear();
      setState(() {
        enrollId = null;
        enrollUri = null;
        enrollSecret = null;
      });
      await _load();
      if (mounted) toast(context, 'Two-step verification is on');
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => busy = false);
  }

  Future<void> _disable(Factor f) async {
    final ok = await confirm(context, title: 'Turn off two-step verification?', confirmLabel: 'Turn off', danger: true);
    if (!ok || !mounted) return;
    await guard(context, () => mfa.unenroll(f.id), success: 'Two-step verification is off');
    await Supabase.instance.client.auth.refreshSession().then((_) {}, onError: (_) {});
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final list = factors;
    return Scaffold(
      appBar: AppBar(title: const Text('Two-step verification')),
      body: list == null
          ? const CenteredLoader()
          : ListView(padding: const EdgeInsets.all(20), children: [
              const Icon(Icons.verified_user_rounded, size: 56, color: HimeColors.yellowDeep),
              const SizedBox(height: 12),
              Text(
                'Add an extra layer of security. When signing in on a new device you\'ll also need a code from an authenticator app (like Google Authenticator or Authy).',
                textAlign: TextAlign.center,
                style: context.text.bodyMedium,
              ),
              const SizedBox(height: 24),
              if (list.isNotEmpty) ...[
                for (final f in list)
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.check_circle_rounded, color: HimeColors.online),
                      title: const Text('Authenticator app'),
                      subtitle: Text('Added ${Fmt.dayLabel(f.createdAt)}'),
                      trailing: TextButton(onPressed: () => _disable(f), child: const Text('Turn off')),
                    ),
                  ),
              ] else if (enrollUri == null)
                PrimaryButton(label: 'Turn on', loading: busy, onPressed: busy ? null : _start)
              else ...[
                Text('1. Scan this QR code with your authenticator app', style: context.text.titleSmall),
                const SizedBox(height: 12),
                Center(
                  child: Container(
                    color: Colors.white,
                    padding: const EdgeInsets.all(12),
                    child: QrImageView(data: enrollUri!, size: 200),
                  ),
                ),
                const SizedBox(height: 12),
                if (enrollSecret != null)
                  Row(children: [
                    Expanded(child: SelectableText('Or enter this key: $enrollSecret', style: const TextStyle(fontFamily: 'monospace'))),
                    IconButton(
                      icon: const Icon(Icons.copy_rounded),
                      onPressed: () {
                        Clipboard.setData(ClipboardData(text: enrollSecret!));
                        toast(context, 'Key copied');
                      },
                    ),
                  ]),
                const SizedBox(height: 16),
                Text('2. Enter the 6-digit code it shows', style: context.text.titleSmall),
                const SizedBox(height: 8),
                HimeField(
                  controller: _code,
                  label: 'Code',
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                ),
                const SizedBox(height: 12),
                PrimaryButton(label: 'Verify and turn on', loading: busy, onPressed: busy ? null : _verify),
              ],
            ]),
    );
  }
}

class DevicesScreen extends ConsumerStatefulWidget {
  const DevicesScreen({super.key});

  @override
  ConsumerState<DevicesScreen> createState() => _DevicesScreenState();
}

class _DevicesScreenState extends ConsumerState<DevicesScreen> {
  late final HimeCore core = ref.read(coreProvider);
  List<Map<String, dynamic>>? devices;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final rows = await core.sb
          .from('user_devices')
          .select('id, name, platform, app_version, created_at, last_active_at')
          .order('last_active_at', ascending: false);
      if (mounted) setState(() => devices = rows);
    } catch (e) {
      if (mounted) {
        setState(() => devices = []);
        toast(context, friendlyError(e));
      }
    }
  }

  Future<void> _remove(Map<String, dynamic> d) async {
    final ok = await confirm(context,
        title: 'Remove "${d['name']}"?',
        message: 'New messages will no longer be encrypted for that device. To fully sign it out, also use "Sign out other sessions".',
        confirmLabel: 'Remove',
        danger: true);
    if (!ok || !mounted) return;
    await guard(context, () => core.sb.from('user_devices').delete().eq('id', d['id'] as String));
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final list = devices;
    return Scaffold(
      appBar: AppBar(title: const Text('Linked devices')),
      body: list == null
          ? const CenteredLoader()
          : ListView(children: [
              Padding(
                padding: const EdgeInsets.all(20),
                child: Text(
                  'Each device has its own encryption key. Messages are encrypted separately for every device listed here.',
                  style: context.text.bodyMedium?.copyWith(color: context.palette.muted),
                ),
              ),
              SettingsGroup(children: [
                for (final d in list)
                  ListTile(
                    leading: Icon(d['platform'] == 'android' ? Icons.phone_android_rounded : Icons.devices_other_rounded),
                    title: Text('${d['name'] ?? 'Device'}${d['id'] == core.deviceId ? ' (this device)' : ''}'),
                    subtitle: Text(
                        'Hime ${d['app_version'] ?? ''} · active ${Fmt.lastSeen(parseTime(d['last_active_at'])).replaceFirst('last seen ', '')}'),
                    trailing: d['id'] == core.deviceId
                        ? null
                        : IconButton(tooltip: 'Remove', icon: const Icon(Icons.close_rounded), onPressed: () => _remove(d)),
                  ),
              ]),
              SettingsGroup(children: [
                SettingsTile(
                  icon: Icons.logout_rounded,
                  title: 'Sign out other sessions',
                  danger: true,
                  onTap: () async {
                    final ok = await confirm(context, title: 'Sign out all other sessions?', confirmLabel: 'Sign out', danger: true);
                    if (!ok || !context.mounted) return;
                    await guard(context, () async {
                      await core.sb.auth.signOut(scope: SignOutScope.others);
                      for (final d in list.where((d) => d['id'] != core.deviceId)) {
                        await core.sb.from('user_devices').delete().eq('id', d['id'] as String);
                      }
                    }, success: 'Other sessions signed out');
                    await _load();
                  },
                ),
              ]),
            ]),
    );
  }
}

// ---------------------------------------------------------------- notifications

class NotificationSettingsScreen extends ConsumerStatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  ConsumerState<NotificationSettingsScreen> createState() => _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState extends ConsumerState<NotificationSettingsScreen> {
  late final HimeCore core = ref.read(coreProvider);
  Map<String, dynamic>? s;
  bool? permitted;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final status = await Permission.notification.status;
    try {
      final row = await core.sb.from('user_notification_settings').select().eq('user_id', core.userId).maybeSingle();
      if (mounted) {
        setState(() {
          s = row ?? {};
          permitted = status.isGranted;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          s = {};
          permitted = status.isGranted;
        });
      }
    }
  }

  Future<void> _set(String key, bool value) async {
    setState(() => s = {...?s, key: value});
    if (key == 'show_preview') await NotificationService.instance.setPreviews(value);
    if (!mounted) return;
    final ok = await guard(context, () => core.sb.from('user_notification_settings').update({key: value}).eq('user_id', core.userId));
    if (!ok && mounted) setState(() => s = {...?s, key: !value});
  }

  @override
  Widget build(BuildContext context) {
    final v = s;
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: v == null
          ? const CenteredLoader()
          : ListView(children: [
              if (permitted == false)
                Card(
                  margin: const EdgeInsets.all(16),
                  color: HimeColors.yellowSoft,
                  child: ListTile(
                    leading: const Icon(Icons.notifications_off_rounded, color: HimeColors.ink),
                    title: const Text('Notifications are off for Hime', style: TextStyle(color: HimeColors.ink)),
                    subtitle: const Text('Turn them on to hear about new messages and calls.', style: TextStyle(color: HimeColors.inkSoft)),
                    trailing: TextButton(
                      onPressed: () async {
                        await NotificationService.instance.requestPermission();
                        final st = await Permission.notification.status;
                        if (!st.isGranted) await openAppSettings();
                        await _load();
                      },
                      child: const Text('Turn on'),
                    ),
                  ),
                ),
              if (!AppConfig.instance.pushConfigured)
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                  child: Text(
                    'Background push isn\'t configured on this server yet, so notifications arrive while Hime is open or running in the background.',
                    style: context.text.bodySmall?.copyWith(color: context.palette.muted),
                  ),
                ),
              SettingsGroup(title: 'Notify me about', children: [
                SwitchListTile(title: const Text('Messages'), value: v['messages'] != false, onChanged: (x) => _set('messages', x)),
                SwitchListTile(title: const Text('Group messages'), value: v['groups'] != false, onChanged: (x) => _set('groups', x)),
                SwitchListTile(title: const Text('Calls'), value: v['calls'] != false, onChanged: (x) => _set('calls', x)),
                SwitchListTile(title: const Text('Status reactions'), value: v['status'] != false, onChanged: (x) => _set('status', x)),
              ]),
              SettingsGroup(children: [
                SwitchListTile(
                  title: const Text('Show message preview'),
                  subtitle: const Text('Show the message text in notifications'),
                  value: v['show_preview'] != false,
                  onChanged: (x) => _set('show_preview', x),
                ),
                SettingsTile(icon: Icons.tune_rounded, title: 'System notification settings', onTap: openAppSettings),
              ]),
            ]),
    );
  }
}

// ---------------------------------------------------------------- chats

class ChatSettingsScreen extends ConsumerStatefulWidget {
  const ChatSettingsScreen({super.key});

  @override
  ConsumerState<ChatSettingsScreen> createState() => _ChatSettingsScreenState();
}

class _ChatSettingsScreenState extends ConsumerState<ChatSettingsScreen> {
  @override
  Widget build(BuildContext context) {
    final prefs = ref.watch(sharedPrefsProvider);
    final enterSends = prefs.getBool('enter_sends') ?? false;
    final core = ref.watch(coreProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Chats')),
      body: ListView(children: [
        SettingsGroup(children: [
          SettingsTile(icon: Icons.palette_outlined, title: 'Theme', onTap: () => context.push('/settings/appearance')),
          SwitchListTile(
            secondary: const Icon(Icons.keyboard_return_rounded),
            title: const Text('Enter is send'),
            subtitle: const Text('The Enter key sends your message'),
            value: enterSends,
            onChanged: (v) async {
              await prefs.setBool('enter_sends', v);
              setState(() {});
            },
          ),
        ]),
        SettingsGroup(children: [
          SettingsTile(icon: Icons.archive_outlined, title: 'Archived chats', onTap: () => context.push('/archived')),
          SettingsTile(
            icon: Icons.archive_rounded,
            title: 'Archive all chats',
            onTap: () async {
              final ok = await confirm(context, title: 'Archive all chats?', confirmLabel: 'Archive');
              if (!ok || !context.mounted) return;
              await guard(context, () async {
                for (final c in core.chatList.active) {
                  await core.chatList.setArchived(c.id, true);
                }
              });
            },
          ),
          SettingsTile(
            icon: Icons.cleaning_services_outlined,
            title: 'Clear all chats',
            danger: true,
            onTap: () async {
              final ok = await confirm(context,
                  title: 'Clear all chats?', message: 'All messages will be removed from this phone.', confirmLabel: 'Clear', danger: true);
              if (!ok || !context.mounted) return;
              await guard(context, () async {
                for (final c in [...core.chatList.chats]) {
                  await core.chats.clearChat(c.id);
                }
              }, success: 'Chats cleared');
            },
          ),
        ]),
      ]),
    );
  }
}

// ---------------------------------------------------------------- storage

class StorageScreen extends ConsumerStatefulWidget {
  const StorageScreen({super.key});

  @override
  ConsumerState<StorageScreen> createState() => _StorageScreenState();
}

class _StorageScreenState extends ConsumerState<StorageScreen> {
  int? media;
  int? cache;
  int? pending;
  bool clearing = false;

  @override
  void initState() {
    super.initState();
    _measure();
  }

  static Future<int> _size(Directory d) async {
    if (!await d.exists()) return 0;
    var total = 0;
    await for (final e in d.list(recursive: true, followLinks: false)) {
      if (e is File) {
        try {
          total += await e.length();
        } catch (_) {}
      }
    }
    return total;
  }

  Future<void> _measure() async {
    final support = await getApplicationSupportDirectory();
    final tmp = await getTemporaryDirectory();
    final m = await _size(Directory(p.join(support.path, 'media')));
    final o = await _size(Directory(p.join(support.path, 'outbox')));
    final c = await _size(tmp);
    if (mounted) {
      setState(() {
        media = m;
        pending = o;
        cache = c;
      });
    }
  }

  Future<void> _clear() async {
    final ok = await confirm(context,
        title: 'Clear downloaded media?',
        message: 'Photos, videos and files will be downloaded again when you open them.',
        confirmLabel: 'Clear',
        danger: true);
    if (!ok || !mounted) return;
    setState(() => clearing = true);
    try {
      final core = ref.read(coreProvider);
      final support = await getApplicationSupportDirectory();
      final dir = Directory(p.join(support.path, 'media'));
      if (await dir.exists()) await dir.delete(recursive: true);
      await core.db.clearMediaIndex();
      final tmp = await getTemporaryDirectory();
      await for (final e in tmp.list(followLinks: false)) {
        try {
          await e.delete(recursive: true);
        } catch (_) {}
      }
      PaintingBinding.instance.imageCache.clear();
      SignedUrls.clear();
    } catch (e) {
      if (mounted) toast(context, friendlyError(e));
    }
    if (mounted) setState(() => clearing = false);
    await _measure();
  }

  @override
  Widget build(BuildContext context) {
    String f(int? v) => v == null ? '…' : Fmt.bytes(v);
    return Scaffold(
      appBar: AppBar(title: const Text('Storage and data')),
      body: ListView(children: [
        SettingsGroup(title: 'On this phone', children: [
          ListTile(leading: const Icon(Icons.perm_media_outlined), title: const Text('Downloaded media'), trailing: Text(f(media))),
          ListTile(leading: const Icon(Icons.cached_rounded), title: const Text('Cache'), trailing: Text(f(cache))),
          ListTile(leading: const Icon(Icons.outbox_outlined), title: const Text('Waiting to send'), trailing: Text(f(pending))),
        ]),
        Padding(
          padding: const EdgeInsets.all(16),
          child: PrimaryButton(label: 'Clear downloaded media and cache', icon: Icons.delete_sweep_outlined, loading: clearing, onPressed: clearing ? null : _clear),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Text(
            'Small photos download automatically. Larger photos, videos and documents download when you tap them, which saves mobile data.',
            style: context.text.bodySmall?.copyWith(color: context.palette.muted),
          ),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- appearance & language

class AppearanceScreen extends ConsumerWidget {
  const AppearanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(themeModeProvider);
    Widget option(ThemeMode m, String label, IconData icon) => ListTile(
          leading: Icon(icon),
          title: Text(label),
          trailing: Icon(mode == m ? Icons.radio_button_checked_rounded : Icons.radio_button_unchecked_rounded,
              color: mode == m ? HimeColors.yellowDeep : null),
          onTap: () => ref.read(themeModeProvider.notifier).set(m),
        );
    return Scaffold(
      appBar: AppBar(title: const Text('Appearance')),
      body: ListView(children: [
        SettingsGroup(title: 'Theme', children: [
          option(ThemeMode.system, 'System default', Icons.brightness_auto_rounded),
          option(ThemeMode.light, 'Light', Icons.light_mode_rounded),
          option(ThemeMode.dark, 'Dark', Icons.dark_mode_rounded),
        ]),
      ]),
    );
  }
}

class LanguageScreen extends StatelessWidget {
  const LanguageScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('App language')),
      body: ListView(children: [
        const ListTile(
          leading: Icon(Icons.check_rounded, color: HimeColors.yellowDeep),
          title: Text('English'),
          subtitle: Text('Device language'),
        ),
        Padding(
          padding: const EdgeInsets.all(20),
          child: Text(
            'Hime is currently available in English. Hindi and other Indian languages are being translated.',
            style: context.text.bodySmall?.copyWith(color: context.palette.muted),
          ),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- help, about, legal

class HelpScreen extends StatelessWidget {
  const HelpScreen({super.key});

  static const _faq = [
    ('Are my messages private?',
        'Yes. Messages, media, voice notes and calls are end-to-end encrypted on your phone. The Hime server only stores encrypted data it cannot read.'),
    ('Why does a message say "Waiting for this message"?',
        'It was encrypted for a device key that this phone doesn\'t have — for example, if it was sent before you signed in on this phone. New messages will arrive normally.'),
    ('How do I verify a contact?',
        'Open the chat, tap the name at the top, then Encryption. Compare the security code with your contact in person or on a call.'),
    ('How do I find friends?',
        'Search for their @username from New chat, or tap "Find friends from phone contacts". Phone numbers are hashed on your phone before matching.'),
    ('How long do status updates last?', 'Status updates disappear automatically after 24 hours.'),
    ('Calls don\'t connect on my network',
        'Some networks block direct connections. Calls then need a relay (TURN) server configured by the Hime server owner.'),
    ('How do I delete my account?', 'Settings → Account → Delete my account. This permanently removes your data.'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Help')),
      body: ListView(children: [
        for (final (q, a) in _faq)
          ExpansionTile(
            title: Text(q, style: const TextStyle(fontWeight: FontWeight.w600)),
            childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            children: [Text(a)],
          ),
        SettingsGroup(children: [
          SettingsTile(icon: Icons.description_outlined, title: 'Privacy policy', onTap: () => context.push('/settings/legal/privacy')),
          SettingsTile(icon: Icons.gavel_rounded, title: 'Terms of service', onTap: () => context.push('/settings/legal/terms')),
        ]),
      ]),
    );
  }
}

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('About')),
      body: ListView(padding: const EdgeInsets.all(24), children: [
        const SizedBox(height: 12),
        const Center(child: HimeLogo(size: 72, tagline: true)),
        const SizedBox(height: 16),
        FutureBuilder<PackageInfo>(
          future: PackageInfo.fromPlatform(),
          builder: (context, snap) => Text(
            snap.hasData ? 'Version ${snap.data!.version} (${snap.data!.buildNumber})' : '',
            textAlign: TextAlign.center,
            style: context.text.bodyMedium?.copyWith(color: context.palette.muted),
          ),
        ),
        const SizedBox(height: 24),
        Text(
          'Hime is a private messaging and calling app. Your conversations are end-to-end encrypted, and we collect only what is needed to deliver your messages.',
          textAlign: TextAlign.center,
          style: context.text.bodyMedium,
        ),
        const SizedBox(height: 24),
        SettingsGroup(children: [
          SettingsTile(icon: Icons.description_outlined, title: 'Privacy policy', onTap: () => context.push('/settings/legal/privacy')),
          SettingsTile(icon: Icons.gavel_rounded, title: 'Terms of service', onTap: () => context.push('/settings/legal/terms')),
          SettingsTile(
            icon: Icons.code_rounded,
            title: 'Open-source licences',
            onTap: () => showLicensePage(context: context, applicationName: 'Hime', applicationLegalese: 'Made with love in India 🇮🇳'),
          ),
        ]),
        const SizedBox(height: 24),
        Center(child: Text('Made with love in India 🇮🇳', style: context.text.titleSmall)),
      ]),
    );
  }
}

class LegalScreen extends StatelessWidget {
  const LegalScreen({super.key, required this.doc});
  final String doc;

  @override
  Widget build(BuildContext context) {
    final terms = doc == 'terms';
    final text = terms ? termsOfService : privacyPolicy;
    return Scaffold(
      appBar: AppBar(title: Text(terms ? 'Terms of service' : 'Privacy policy')),
      body: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 40), children: [
        for (final block in text.trim().split('\n\n'))
          Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: block.startsWith('# ')
                ? Text(block.substring(2), style: context.text.titleMedium)
                : Text(block, style: context.text.bodyMedium?.copyWith(height: 1.5)),
          ),
      ]),
    );
  }
}
