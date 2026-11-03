import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/config.dart';
import '../../core/countries.dart';
import '../../core/theme.dart';
import '../../core/utils.dart';
import '../../core/widgets.dart';
import '../../services/session.dart';

SupabaseClient get _sb => Supabase.instance.client;

class _AuthScaffold extends StatelessWidget {
  const _AuthScaffold({required this.title, this.subtitle, required this.children, this.showBack = true});
  final String title;
  final String? subtitle;
  final List<Widget> children;
  final bool showBack;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(automaticallyImplyLeading: showBack),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          children: [
            Text(title, style: context.text.headlineMedium),
            if (subtitle != null) ...[
              const SizedBox(height: 8),
              Text(subtitle!, style: context.text.bodyMedium?.copyWith(color: context.palette.muted)),
            ],
            const SizedBox(height: 28),
            ...children,
          ],
        ),
      ),
    );
  }
}

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Spacer(),
            Center(
              child: TweenAnimationBuilder<double>(
                tween: Tween(begin: 0.85, end: 1),
                duration: const Duration(milliseconds: 600),
                curve: Curves.easeOutBack,
                builder: (_, v, child) => Transform.scale(scale: v, child: child),
                child: Container(
                  width: 132,
                  height: 132,
                  decoration: BoxDecoration(
                    color: HimeColors.yellow,
                    borderRadius: BorderRadius.circular(36),
                    boxShadow: [BoxShadow(color: HimeColors.yellow.withValues(alpha: 0.45), blurRadius: 32, offset: const Offset(0, 12))],
                  ),
                  padding: const EdgeInsets.all(22),
                  child: Image.asset('assets/images/hime_mark.png'),
                ),
              ),
            ),
            const SizedBox(height: 36),
            Text('Hime', textAlign: TextAlign.center, style: context.text.displaySmall),
            const SizedBox(height: 8),
            Text('Connect Without Limits.',
                textAlign: TextAlign.center, style: context.text.titleMedium?.copyWith(color: context.palette.muted)),
            const SizedBox(height: 18),
            _Feature(icon: Icons.lock_rounded, text: 'End-to-end encrypted messages and media'),
            _Feature(icon: Icons.videocam_rounded, text: 'Crystal-clear voice and video calls'),
            _Feature(icon: Icons.bolt_rounded, text: 'Fast and light, even on budget phones'),
            const Spacer(),
            PrimaryButton(label: 'Continue with email', onPressed: () => context.push('/auth/email')),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => context.push('/auth/phone'),
              icon: const Icon(Icons.phone_iphone_rounded),
              label: const Text('Continue with phone'),
            ),
            const SizedBox(height: 8),
            TextButton(onPressed: () => context.push('/auth/email?mode=password'), child: const Text('Sign in with password')),
            const SizedBox(height: 6),
            Text('Made with love in India 🇮🇳', textAlign: TextAlign.center, style: context.text.labelSmall),
          ]),
        ),
      ),
    );
  }
}

class _Feature extends StatelessWidget {
  const _Feature({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5, horizontal: 12),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon, size: 18, color: HimeColors.yellowDeep),
          const SizedBox(width: 10),
          Flexible(child: Text(text, style: context.text.bodyMedium)),
        ]),
      );
}

/// Email sign-in. By default Hime emails a one-time code (new accounts are
/// created automatically); a password can be used instead for accounts that
/// have one.
class EmailAuthScreen extends StatefulWidget {
  const EmailAuthScreen({super.key, this.usePassword = false});
  final bool usePassword;

  @override
  State<EmailAuthScreen> createState() => _EmailAuthScreenState();
}

class _EmailAuthScreenState extends State<EmailAuthScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  late bool _usePassword = widget.usePassword;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    final email = _email.text.trim().toLowerCase();
    try {
      if (_usePassword) {
        await _sb.auth.signInWithPassword(email: email, password: _password.text);
      } else {
        await sendEmailCode(email);
        if (mounted) context.push('/auth/otp', extra: OtpArgs(email: email));
      }
    } catch (e) {
      final msg = friendlyError(e);
      if (_usePassword && msg.contains('verify your email')) {
        // Unconfirmed account: confirm it with a code instead.
        try {
          await sendEmailCode(email, create: false);
          if (mounted) context.push('/auth/otp', extra: OtpArgs(email: email));
          return;
        } catch (_) {}
      }
      if (mounted) setState(() => _error = msg);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthScaffold(
      title: _usePassword ? 'Sign in with password' : 'Continue with email',
      subtitle: _usePassword
          ? 'Use the password you set for your Hime account.'
          : 'We\'ll email you a 6-digit code. No password needed — new accounts are created automatically.',
      children: [
        Form(
          key: _form,
          child: AutofillGroup(
            child: Column(children: [
              HimeField(
                controller: _email,
                label: 'Email',
                prefix: const Icon(Icons.alternate_email_rounded),
                keyboardType: TextInputType.emailAddress,
                validator: Validators.email,
                textInputAction: _usePassword ? TextInputAction.next : TextInputAction.done,
                onSubmitted: _usePassword ? null : (_) => _submit(),
                autofillHints: const [AutofillHints.email],
                autofocus: true,
              ),
              AnimatedSize(
                duration: const Duration(milliseconds: 200),
                child: _usePassword
                    ? Padding(
                        padding: const EdgeInsets.only(top: 14),
                        child: HimeField(
                          controller: _password,
                          label: 'Password',
                          obscure: true,
                          prefix: const Icon(Icons.lock_outline_rounded),
                          validator: (v) => Validators.required(v, 'Password'),
                          textInputAction: TextInputAction.done,
                          onSubmitted: (_) => _submit(),
                          autofillHints: const [AutofillHints.password],
                        ),
                      )
                    : const SizedBox(width: double.infinity),
              ),
            ]),
          ),
        ),
        if (_usePassword)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(onPressed: () => context.push('/auth/forgot'), child: const Text('Forgot password?')),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(_error!, style: TextStyle(color: context.colors.error)),
          ),
        const SizedBox(height: 20),
        PrimaryButton(label: _usePassword ? 'Sign in' : 'Send code', loading: _busy, onPressed: _submit),
        const SizedBox(height: 12),
        TextButton(
          onPressed: () => setState(() {
            _usePassword = !_usePassword;
            _error = null;
          }),
          child: Text(_usePassword ? 'Sign in with an email code instead' : 'I have a password'),
        ),
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            'By continuing you agree to Hime\'s Terms and Privacy Policy.',
            textAlign: TextAlign.center,
            style: context.text.labelSmall,
          ),
        ),
      ],
    );
  }
}

/// Emails a one-time sign-in code (the email may also contain a link that
/// opens Hime — either works).
Future<void> sendEmailCode(String email, {bool create = true}) => _sb.auth.signInWithOtp(
      email: email,
      shouldCreateUser: create,
      emailRedirectTo: AppConfig.instance.authRedirectUrl,
    );

/// Verifies an emailed code. New accounts get a "confirm signup" token,
/// existing ones a sign-in token; try both.
Future<void> verifyEmailCode(String email, String code) async {
  try {
    await _sb.auth.verifyOTP(type: OtpType.email, email: email, token: code);
  } on AuthException catch (first) {
    try {
      await _sb.auth.verifyOTP(type: OtpType.signup, email: email, token: code);
    } on AuthException {
      throw first;
    }
  }
}

/// Kept for links to /auth/verify-email: confirms an address with a code.
class VerifyEmailScreen extends StatelessWidget {
  const VerifyEmailScreen({super.key, required this.email});
  final String email;

  @override
  Widget build(BuildContext context) => OtpScreen(args: OtpArgs(email: email, sendOnOpen: true));
}

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _email = TextEditingController();
  final _code = TextEditingController();
  bool _sent = false;
  bool _busy = false;
  String? _message;

  Future<void> _send() async {
    final err = Validators.email(_email.text);
    if (err != null) {
      setState(() => _message = err);
      return;
    }
    setState(() => _busy = true);
    try {
      await _sb.auth.resetPasswordForEmail(_email.text.trim(), redirectTo: AppConfig.instance.authRedirectUrl);
      setState(() {
        _sent = true;
        _message = 'We emailed a code to ${_email.text.trim()}. Enter it below to set a new password.';
      });
    } catch (e) {
      setState(() => _message = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    if (_code.text.trim().length < 6) {
      setState(() => _message = 'Enter the code from the email.');
      return;
    }
    setState(() => _busy = true);
    try {
      await _sb.auth.verifyOTP(type: OtpType.recovery, email: _email.text.trim(), token: _code.text.trim());
    } catch (e) {
      setState(() => _message = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthScaffold(
      title: 'Reset password',
      subtitle: 'We\'ll email you a code to reset it.',
      children: [
        HimeField(
          controller: _email,
          label: 'Email',
          keyboardType: TextInputType.emailAddress,
          prefix: const Icon(Icons.alternate_email_rounded),
        ),
        if (_sent) ...[
          const SizedBox(height: 14),
          HimeField(
            controller: _code,
            label: 'Code from the email',
            keyboardType: TextInputType.number,
            maxLength: 10,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            autofocus: true,
          ),
        ],
        if (_message != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_message!)),
        const SizedBox(height: 20),
        PrimaryButton(
          label: _sent ? 'Verify code' : 'Send code',
          loading: _busy,
          onPressed: _sent ? _verify : _send,
        ),
        if (_sent) TextButton(onPressed: _send, child: const Text('Send again')),
      ],
    );
  }
}

class ResetPasswordScreen extends ConsumerStatefulWidget {
  const ResetPasswordScreen({super.key});

  @override
  ConsumerState<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _form = GlobalKey<FormState>();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  String? _error;

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await _sb.auth.updateUser(UserAttributes(password: _password.text));
      if (mounted) toast(context, 'Password updated');
      await ref.read(sessionProvider).finishRecovery();
    } catch (e) {
      setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthScaffold(
      title: 'Choose a new password',
      showBack: false,
      children: [
        Form(
          key: _form,
          child: Column(children: [
            HimeField(controller: _password, label: 'New password', obscure: true, validator: Validators.password),
            const SizedBox(height: 14),
            HimeField(
              controller: _confirm,
              label: 'Confirm password',
              obscure: true,
              validator: (v) => v != _password.text ? 'Passwords don\'t match' : null,
            ),
          ]),
        ),
        if (_error != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_error!, style: TextStyle(color: context.colors.error))),
        const SizedBox(height: 20),
        PrimaryButton(label: 'Save password', loading: _busy, onPressed: _save),
      ],
    );
  }
}

class OtpArgs {
  const OtpArgs({this.phone, this.email, this.sendOnOpen = false}) : assert(phone != null || email != null);
  final String? phone;
  final String? email;

  /// Send a fresh code when the screen opens (used when confirming an address).
  final bool sendOnOpen;
  bool get isEmail => email != null;
}

class PhoneAuthScreen extends StatefulWidget {
  const PhoneAuthScreen({super.key});

  @override
  State<PhoneAuthScreen> createState() => _PhoneAuthScreenState();
}

class _PhoneAuthScreenState extends State<PhoneAuthScreen> {
  Country _country = countries.first;
  final _number = TextEditingController();
  bool _busy = false;
  String? _error;

  Future<void> _pickCountry() async {
    final picked = await showModalBottomSheet<Country>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => _CountryPicker(selected: _country),
    );
    if (picked != null) setState(() => _country = picked);
  }

  Future<void> _send() async {
    final e164 = Phone.toE164(_number.text, _country.dial);
    if (e164 == null) {
      setState(() => _error = 'Enter a valid phone number');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await _sb.auth.signInWithOtp(phone: e164);
      if (mounted) context.push('/auth/otp', extra: OtpArgs(phone: e164));
    } catch (e) {
      setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthScaffold(
      title: 'Your phone number',
      subtitle: 'We\'ll text you a 6-digit code to verify it.',
      children: [
        Row(children: [
          Pressable(
            onTap: _pickCountry,
            child: Container(
              height: 54,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: BoxDecoration(
                color: context.isDark ? HimeColors.darkSurfaceHigh : const Color(0xFFF4F4F4),
                borderRadius: BorderRadius.circular(HimeRadius.md),
              ),
              child: Row(children: [
                Text(_country.flag, style: const TextStyle(fontSize: 20)),
                const SizedBox(width: 6),
                Text(_country.dial, style: context.text.titleSmall),
                const Icon(Icons.expand_more_rounded, size: 20),
              ]),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: HimeField(
              controller: _number,
              label: 'Phone number',
              keyboardType: TextInputType.phone,
              autofocus: true,
              inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9 ]'))],
              onSubmitted: (_) => _send(),
            ),
          ),
        ]),
        if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: TextStyle(color: context.colors.error))),
        const SizedBox(height: 24),
        PrimaryButton(label: 'Send code', loading: _busy, onPressed: _send),
        const SizedBox(height: 12),
        Text('Carrier SMS charges may apply.', textAlign: TextAlign.center, style: context.text.labelSmall),
      ],
    );
  }
}

class _CountryPicker extends StatefulWidget {
  const _CountryPicker({required this.selected});
  final Country selected;

  @override
  State<_CountryPicker> createState() => _CountryPickerState();
}

class _CountryPickerState extends State<_CountryPicker> {
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final list = countries
        .where((c) => _q.isEmpty || c.name.toLowerCase().contains(_q) || c.dial.contains(_q))
        .toList();
    return SizedBox(
      height: MediaQuery.sizeOf(context).height * 0.8,
      child: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
          child: TextField(
            autofocus: true,
            decoration: const InputDecoration(hintText: 'Search country', prefixIcon: Icon(Icons.search_rounded)),
            onChanged: (v) => setState(() => _q = v.trim().toLowerCase()),
          ),
        ),
        Expanded(
          child: ListView.builder(
            itemCount: list.length,
            itemBuilder: (_, i) {
              final c = list[i];
              return ListTile(
                leading: Text(c.flag, style: const TextStyle(fontSize: 22)),
                title: Text(c.name),
                trailing: Text(c.dial, style: context.text.labelMedium),
                selected: c.iso == widget.selected.iso,
                onTap: () => Navigator.pop(context, c),
              );
            },
          ),
        ),
      ]),
    );
  }
}

class OtpScreen extends StatefulWidget {
  const OtpScreen({super.key, required this.args});
  final OtpArgs args;

  @override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> {
  final _code = TextEditingController();
  bool _busy = false;
  String? _error;
  String? _info;
  int _seconds = 60;
  Timer? _timer;

  OtpArgs get a => widget.args;

  @override
  void initState() {
    super.initState();
    _startTimer();
    if (a.sendOnOpen) WidgetsBinding.instance.addPostFrameCallback((_) => _resend());
  }

  void _startTimer([int seconds = 60]) {
    _timer?.cancel();
    setState(() => _seconds = seconds);
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted || _seconds <= 0) {
        t.cancel();
      } else {
        setState(() => _seconds--);
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _code.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    final code = _code.text.trim();
    if (code.length < 6) {
      setState(() => _error = a.isEmail ? 'Enter the code from the email' : 'Enter the 6-digit code');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      if (a.isEmail) {
        await verifyEmailCode(a.email!, code);
      } else {
        await _sb.auth.verifyOTP(type: OtpType.sms, phone: a.phone!, token: code);
      }
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _resend() async {
    setState(() {
      _error = null;
      _info = null;
    });
    try {
      if (a.isEmail) {
        await sendEmailCode(a.email!);
      } else {
        await _sb.auth.signInWithOtp(phone: a.phone!);
      }
      _startTimer();
      if (mounted) setState(() => _info = 'A new code is on its way.');
    } catch (e) {
      final wait = RegExp(r'after (\d+) seconds').firstMatch(e.toString());
      if (wait != null) _startTimer(int.parse(wait.group(1)!));
      if (mounted) setState(() => _error = friendlyError(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final email = a.isEmail;
    return _AuthScaffold(
      title: email ? 'Check your email' : 'Enter the code',
      subtitle: email
          ? 'Enter the code we sent to ${a.email}. It can take a minute to arrive — check Spam or Promotions too.'
          : 'Sent by SMS to ${a.phone}',
      children: [
        TextField(
          controller: _code,
          autofocus: true,
          keyboardType: TextInputType.number,
          textAlign: TextAlign.center,
          maxLength: email ? 10 : 6,
          autofillHints: const [AutofillHints.oneTimeCode],
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style: context.text.headlineMedium?.copyWith(letterSpacing: 10),
          decoration: InputDecoration(counterText: '', hintText: email ? '••••••' : '••••••'),
          onChanged: (v) {
            if (!email && v.length == 6) _verify();
            if (_error != null) setState(() => _error = null);
          },
          onSubmitted: (_) => _verify(),
        ),
        if (_error != null)
          Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: TextStyle(color: context.colors.error))),
        if (_info != null && _error == null)
          Padding(padding: const EdgeInsets.only(top: 12), child: Text(_info!, style: TextStyle(color: context.palette.muted))),
        const SizedBox(height: 24),
        PrimaryButton(label: 'Verify', loading: _busy, onPressed: _verify),
        const SizedBox(height: 8),
        TextButton(
          onPressed: _seconds > 0 ? null : _resend,
          child: Text(_seconds > 0 ? 'Resend code in ${_seconds}s' : 'Resend code'),
        ),
        if (email)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              'If the email has a button instead of a code, tapping it on this phone signs you in too.',
              textAlign: TextAlign.center,
              style: context.text.labelSmall?.copyWith(color: context.palette.muted),
            ),
          ),
      ],
    );
  }
}

class MfaVerifyScreen extends ConsumerStatefulWidget {
  const MfaVerifyScreen({super.key});

  @override
  ConsumerState<MfaVerifyScreen> createState() => _MfaVerifyScreenState();
}

class _MfaVerifyScreenState extends ConsumerState<MfaVerifyScreen> {
  final _code = TextEditingController();
  bool _busy = false;
  String? _error;

  Future<void> _verify() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final factors = await _sb.auth.mfa.listFactors();
      final totp = factors.totp.where((f) => f.status == FactorStatus.verified).toList();
      if (totp.isEmpty) throw const AuthException('No two-step factor found');
      await _sb.auth.mfa.challengeAndVerify(factorId: totp.first.id, code: _code.text.trim());
      await ref.read(sessionProvider).continueAfterSetup();
    } catch (e) {
      setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthScaffold(
      title: 'Two-step verification',
      subtitle: 'Enter the 6-digit code from your authenticator app.',
      showBack: false,
      children: [
        HimeField(
          controller: _code,
          label: 'Code',
          keyboardType: TextInputType.number,
          maxLength: 6,
          autofocus: true,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          onSubmitted: (_) => _verify(),
        ),
        if (_error != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_error!, style: TextStyle(color: context.colors.error))),
        const SizedBox(height: 20),
        PrimaryButton(label: 'Continue', loading: _busy, onPressed: _verify),
        TextButton(onPressed: () => ref.read(sessionProvider).signOut(), child: const Text('Sign out')),
      ],
    );
  }
}

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _form = GlobalKey<FormState>();
  late final _name = TextEditingController(text: ref.read(sessionProvider).profile?.displayName ?? '');
  final _username = TextEditingController();
  final _about = TextEditingController(text: 'Hey there! I\'m on Hime.');
  final _debounce = Debouncer(const Duration(milliseconds: 450));
  File? _photo;
  bool? _available;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _debounce.dispose();
    super.dispose();
  }

  void _checkUsername(String v) {
    final s = v.trim().toLowerCase();
    setState(() => _available = null);
    if (Validators.username(s) != null) return;
    _debounce(() async {
      try {
        final ok = await _sb.rpc('is_username_available', params: {'p_username': s}) as bool;
        if (mounted && _username.text.trim().toLowerCase() == s) setState(() => _available = ok);
      } catch (_) {}
    });
  }

  Future<void> _pickPhoto() async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 720, maxHeight: 720, imageQuality: 82);
    if (x != null) setState(() => _photo = File(x.path));
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    if (_available == false) {
      setState(() => _error = 'That username is taken');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final uid = _sb.auth.currentUser!.id;
      String? avatarPath;
      if (_photo != null) {
        avatarPath = 'users/$uid/${DateTime.now().millisecondsSinceEpoch}.jpg';
        await _sb.storage.from('avatars').upload(avatarPath, _photo!, fileOptions: const FileOptions(contentType: 'image/jpeg'));
      }
      await _sb.from('profiles').update({
        'display_name': _name.text.trim(),
        'username': _username.text.trim().toLowerCase(),
        'about': _about.text.trim().isEmpty ? 'Hey there! I\'m on Hime.' : _about.text.trim(),
        'avatar_path': ?avatarPath,
        if (avatarPath != null) 'avatar_version': 1,
        'onboarded': true,
      }).eq('id', uid);
      await ref.read(sessionProvider).continueAfterSetup();
    } catch (e) {
      setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthScaffold(
      title: 'Set up your profile',
      subtitle: 'This is how people find and recognise you on Hime.',
      showBack: false,
      children: [
        Center(
          child: Pressable(
            onTap: _pickPhoto,
            child: Stack(children: [
              CircleAvatar(
                radius: 52,
                backgroundColor: context.colors.primaryContainer,
                backgroundImage: _photo == null ? null : FileImage(_photo!),
                child: _photo == null ? const Icon(Icons.person_rounded, size: 52) : null,
              ),
              Positioned(
                right: 0,
                bottom: 0,
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: const BoxDecoration(color: HimeColors.yellow, shape: BoxShape.circle),
                  child: const Icon(Icons.camera_alt_rounded, size: 18, color: HimeColors.ink),
                ),
              ),
            ]),
          ),
        ),
        const SizedBox(height: 24),
        Form(
          key: _form,
          child: Column(children: [
            HimeField(
              controller: _name,
              label: 'Name',
              maxLength: 64,
              textCapitalization: TextCapitalization.words,
              validator: (v) => Validators.required(v, 'Name'),
            ),
            const SizedBox(height: 14),
            HimeField(
              controller: _username,
              label: 'Username',
              prefix: const Icon(Icons.alternate_email_rounded),
              maxLength: 24,
              validator: Validators.username,
              onChanged: _checkUsername,
              inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[a-zA-Z0-9_.]'))],
              suffix: _available == null
                  ? null
                  : Icon(_available! ? Icons.check_circle_rounded : Icons.cancel_rounded,
                      color: _available! ? HimeColors.online : context.colors.error),
            ),
            const SizedBox(height: 14),
            HimeField(controller: _about, label: 'About', maxLength: 140),
          ]),
        ),
        if (_error != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_error!, style: TextStyle(color: context.colors.error))),
        const SizedBox(height: 20),
        PrimaryButton(label: 'Continue', loading: _busy, onPressed: _save),
        TextButton(onPressed: () => ref.read(sessionProvider).signOut(), child: const Text('Sign out')),
      ],
    );
  }
}
