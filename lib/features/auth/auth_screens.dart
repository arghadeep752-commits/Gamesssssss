import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

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

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  /// Email stays available only while the SMS sender isn't set up yet.
  bool _emailFallback = false;

  @override
  void initState() {
    super.initState();
    phoneCodesAvailable().then((ok) {
      if (mounted && !ok) setState(() => _emailFallback = true);
    });
  }

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
            PrimaryButton(label: 'Continue with phone number', onPressed: () => context.push('/auth/phone')),
            const SizedBox(height: 8),
            if (_emailFallback)
              TextButton(onPressed: () => context.push('/auth/email'), child: const Text('Use email instead'))
            else
              Text('Your number is only used to sign in and to help friends find you.',
                  textAlign: TextAlign.center, style: context.text.labelSmall?.copyWith(color: context.palette.muted)),
            const SizedBox(height: 10),
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

/// Errors from the email-auth function, phrased for people.
class EmailAuthError implements UserFacingException {
  EmailAuthError(this.code, {this.seconds});
  final String code;
  final int? seconds;

  @override
  String toString() => switch (code) {
        'invalid_email' => 'Enter a valid email address.',
        'email_not_configured' => 'Email codes aren\'t switched on yet. Use your password for now.',
        'wait' => 'Please wait ${seconds ?? 60} seconds before asking for a new code.',
        'rate_limited' => 'Too many attempts. Please try again in a little while.',
        'code_expired' => 'That code has expired. Ask for a new one.',
        'invalid_code' => 'That code is wrong. Check the email and try again.',
        'too_many_attempts' => 'Too many wrong tries. Ask for a new code.',
        'weak_password' => 'Use at least 8 characters with letters and numbers.',
        'email_exists' => 'An account with this email already exists. Sign in instead.',
        'send_failed' => 'Couldn\'t send the email right now. Please try again in a minute.',
        _ => 'Something went wrong. Please try again.',
      };
}

Future<Map<String, dynamic>> _emailAuth(Map<String, dynamic> body) async {
  try {
    final res = await _sb.functions.invoke('email-auth', body: body);
    final data = res.data;
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  } on FunctionException catch (e) {
    var details = e.details;
    if (details is String) {
      try {
        details = jsonDecode(details);
      } catch (_) {}
    }
    final m = details is Map ? Map<String, dynamic>.from(details) : const <String, dynamic>{};
    throw EmailAuthError(m['error']?.toString() ?? 'server_error', seconds: (m['seconds'] as num?)?.toInt());
  }
}

/// Whether the server can email 6-digit codes (an email account is configured).
Future<bool> emailCodesAvailable() async {
  try {
    return (await _emailAuth({'action': 'config'}))['otp'] == true;
  } catch (_) {
    return false;
  }
}

/// Emails a 6-digit code (always a number, never a link).
Future<void> sendEmailCode(String email) => _emailAuth({'action': 'send_code', 'email': email});

/// Checks the code and signs in. A [password] sets (or resets) the account password.
Future<void> verifyEmailCode(String email, String code, {String? password}) async {
  final r = await _emailAuth({'action': 'verify_code', 'email': email, 'code': code, 'password': ?password});
  final hash = r['token_hash'] as String?;
  if (hash == null) throw EmailAuthError('server_error');
  await _sb.auth.verifyOTP(type: OtpType.magiclink, tokenHash: hash);
}

/// Errors from the phone-auth function, phrased for people.
class PhoneAuthError implements UserFacingException {
  PhoneAuthError(this.code, {this.seconds, this.prefixes});
  final String code;
  final int? seconds;
  final List<String>? prefixes;

  @override
  String toString() => switch (code) {
        'invalid_phone' => 'Enter a valid mobile number.',
        'sms_not_configured' => 'Phone verification isn\'t switched on yet. Please try again a little later.',
        'country_not_supported' =>
          'Hime currently works with ${(prefixes ?? const ['+91']).join(', ')} numbers only.',
        'wait' => 'Please wait ${seconds ?? 60} seconds before asking for a new code.',
        'rate_limited' => 'Too many attempts. Please try again in a little while.',
        'daily_limit' => 'Hime has sent its maximum number of codes for today. Please try again tomorrow.',
        'code_expired' => 'That code has expired. Ask for a new one.',
        'invalid_code' => 'That code is wrong. Check the SMS and try again.',
        'too_many_attempts' => 'Too many wrong tries. Ask for a new code.',
        'phone_in_use' => 'This number already belongs to another Hime account.',
        'send_failed' => 'Couldn\'t send the SMS right now. Please try again in a minute.',
        'missing_token' || 'invalid_token' => 'Please sign in again.',
        _ => 'Something went wrong. Please try again.',
      };
}

Future<Map<String, dynamic>> _phoneAuth(Map<String, dynamic> body) async {
  try {
    // The access token (when signed in) goes along automatically; "link" needs it.
    final res = await _sb.functions.invoke('phone-auth', body: body);
    final data = res.data;
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  } on FunctionException catch (e) {
    var details = e.details;
    if (details is String) {
      try {
        details = jsonDecode(details);
      } catch (_) {}
    }
    final m = details is Map ? Map<String, dynamic>.from(details) : const <String, dynamic>{};
    throw PhoneAuthError(
      m['error']?.toString() ?? 'server_error',
      seconds: (m['seconds'] as num?)?.toInt(),
      prefixes: (m['prefixes'] as List?)?.map((e) => '$e').toList(),
    );
  }
}

/// Whether the server can text 6-digit codes (the SMS sender is set up).
Future<bool> phoneCodesAvailable() async {
  try {
    return (await _phoneAuth({'action': 'config'}))['sms'] == true;
  } catch (_) {
    // Can't tell (offline): keep phone sign-in as the only option.
    return true;
  }
}

/// Texts a 6-digit code to [phone] (E.164).
Future<void> sendPhoneCode(String phone) => _phoneAuth({'action': 'send_code', 'phone': phone});

/// Checks the code and signs in (creating the account on first sign-in).
Future<void> verifyPhoneCode(String phone, String code) async {
  final r = await _phoneAuth({'action': 'verify_code', 'phone': phone, 'code': code});
  final hash = r['token_hash'] as String?;
  if (hash == null) throw PhoneAuthError('server_error');
  await _sb.auth.verifyOTP(type: OtpType.magiclink, tokenHash: hash);
}

/// Adds or changes the phone number of the signed-in account.
Future<void> linkPhoneCode(String phone, String code) async {
  await _phoneAuth({'action': 'link', 'phone': phone, 'code': code});
  // Pick up the new number in the local session.
  try {
    await _sb.auth.refreshSession();
  } catch (_) {}
}

/// Email + password sign-in and account creation.
class EmailAuthScreen extends StatefulWidget {
  const EmailAuthScreen({super.key, this.signUp = false});
  final bool signUp;

  @override
  State<EmailAuthScreen> createState() => _EmailAuthScreenState();
}

class _EmailAuthScreenState extends State<EmailAuthScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  late bool _signUp = widget.signUp;
  bool? _codes;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    emailCodesAvailable().then((v) {
      if (mounted) setState(() => _codes = v);
    });
  }

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  String get _emailValue => _email.text.trim().toLowerCase();

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    final email = _emailValue;
    final password = _password.text;
    await _run(() async {
      if (_signUp) {
        if (_codes ?? await emailCodesAvailable()) {
          await sendEmailCode(email);
          if (mounted) context.push('/auth/otp', extra: OtpArgs(email: email, password: password));
        } else {
          await _emailAuth({'action': 'signup', 'email': email, 'password': password});
          await _sb.auth.signInWithPassword(email: email, password: password);
        }
        return;
      }
      try {
        await _sb.auth.signInWithPassword(email: email, password: password);
      } on AuthException catch (e) {
        final unconfirmed = e.message.toLowerCase().contains('not confirmed');
        if (unconfirmed && (_codes ?? false)) {
          // Older account that was never verified: verify it with a code now.
          await sendEmailCode(email);
          if (mounted) context.push('/auth/otp', extra: OtpArgs(email: email, password: password));
          return;
        }
        rethrow;
      }
    });
  }

  Future<void> _codeLogin() async {
    final email = _emailValue;
    if (Validators.email(email) != null) {
      setState(() => _error = 'Enter your email first.');
      return;
    }
    await _run(() async {
      await sendEmailCode(email);
      if (mounted) context.push('/auth/otp', extra: OtpArgs(email: email));
    });
  }

  @override
  Widget build(BuildContext context) {
    final codes = _codes ?? false;
    return _AuthScaffold(
      title: _signUp ? 'Create your account' : 'Welcome back',
      subtitle: _signUp
          ? (codes
              ? 'We\'ll email you a 6-digit code to confirm it\'s you.'
              : 'Your account is ready as soon as you tap Create account.')
          : 'Sign in with your email and password.',
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
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.email],
                autofocus: true,
              ),
              const SizedBox(height: 14),
              HimeField(
                controller: _password,
                label: _signUp ? 'Create a password' : 'Password',
                obscure: true,
                prefix: const Icon(Icons.lock_outline_rounded),
                validator: _signUp ? Validators.password : (v) => Validators.required(v, 'Password'),
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => _submit(),
                autofillHints: [_signUp ? AutofillHints.newPassword : AutofillHints.password],
              ),
            ]),
          ),
        ),
        if (!_signUp)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => codes
                  ? context.push('/auth/forgot', extra: _emailValue)
                  : setState(() => _error = 'Password reset by email isn\'t switched on yet.'),
              child: const Text('Forgot password?'),
            ),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(_error!, style: TextStyle(color: context.colors.error)),
          ),
        const SizedBox(height: 20),
        PrimaryButton(label: _signUp ? 'Create account' : 'Sign in', loading: _busy, onPressed: _submit),
        if (!_signUp && codes) ...[
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _busy ? null : _codeLogin,
            icon: const Icon(Icons.pin_outlined),
            label: const Text('Sign in with an email code'),
          ),
        ],
        const SizedBox(height: 8),
        TextButton(
          onPressed: () => setState(() {
            _signUp = !_signUp;
            _error = null;
          }),
          child: Text(_signUp ? 'Already have an account? Sign in' : 'New to Hime? Create an account'),
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

/// Kept for links to /auth/verify-email: confirms an address with a code.
class VerifyEmailScreen extends StatelessWidget {
  const VerifyEmailScreen({super.key, required this.email});
  final String email;

  @override
  Widget build(BuildContext context) => OtpScreen(args: OtpArgs(email: email, sendOnOpen: true));
}

/// Forgot password: email a code, then choose a new password on the code screen.
class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key, this.email});
  final String? email;

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  late final _email = TextEditingController(text: widget.email ?? '');
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final email = _email.text.trim().toLowerCase();
    if (Validators.email(email) != null) {
      setState(() => _error = 'Enter a valid email address.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await sendEmailCode(email);
      if (mounted) context.pushReplacement('/auth/otp', extra: OtpArgs(email: email, reset: true));
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthScaffold(
      title: 'Reset password',
      subtitle: 'We\'ll email you a 6-digit code. Then you can choose a new password.',
      children: [
        HimeField(
          controller: _email,
          label: 'Email',
          keyboardType: TextInputType.emailAddress,
          prefix: const Icon(Icons.alternate_email_rounded),
          autofocus: true,
          onSubmitted: (_) => _send(),
        ),
        if (_error != null)
          Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: TextStyle(color: context.colors.error))),
        const SizedBox(height: 20),
        PrimaryButton(label: 'Send code', loading: _busy, onPressed: _send),
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
  const OtpArgs({this.phone, this.email, this.password, this.reset = false, this.sendOnOpen = false, this.link = false})
      : assert(phone != null || email != null);
  final String? phone;
  final String? email;

  /// Add/change the phone number of the signed-in account instead of signing in.
  final bool link;

  /// Password to set once the code is confirmed (new accounts).
  final String? password;

  /// Ask for a new password on the code screen (forgot password).
  final bool reset;

  /// Send a fresh code when the screen opens.
  final bool sendOnOpen;
  bool get isEmail => email != null;
}

class PhoneAuthScreen extends StatefulWidget {
  const PhoneAuthScreen({super.key, this.link = false});

  /// Opened from Settings to add or change the account's number.
  final bool link;

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
      await sendPhoneCode(e164);
      if (!mounted) return;
      final args = OtpArgs(phone: e164, link: widget.link);
      if (widget.link) {
        final ok = await context.push<bool>('/settings/phone/verify', extra: args);
        if (ok == true && mounted) context.pop(true);
      } else {
        context.push('/auth/otp', extra: args);
      }
    } catch (e) {
      if (e is PhoneAuthError && e.code == 'wait' && mounted) {
        // A code was sent a moment ago: go on and enter it.
        final args = OtpArgs(phone: e164, link: widget.link);
        if (widget.link) {
          final ok = await context.push<bool>('/settings/phone/verify', extra: args);
          if (ok == true && mounted) context.pop(true);
        } else {
          context.push('/auth/otp', extra: args);
        }
        return;
      }
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthScaffold(
      title: widget.link ? 'Your phone number' : 'Enter your phone number',
      subtitle: widget.link
          ? 'We\'ll text a 6-digit code to the new number to confirm it.'
          : 'Hime will send you an SMS with a 6-digit code to verify your number.',
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
        Text('Receiving the SMS is free.', textAlign: TextAlign.center, style: context.text.labelSmall),
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
  final _newPassword = TextEditingController();
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
    _newPassword.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    final code = _code.text.trim();
    if (code.length != 6) {
      setState(() => _error = 'Enter the 6-digit code');
      return;
    }
    if (a.reset) {
      final weak = Validators.password(_newPassword.text);
      if (weak != null) {
        setState(() => _error = weak);
        return;
      }
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      if (a.isEmail) {
        await verifyEmailCode(a.email!, code, password: a.reset ? _newPassword.text : a.password);
      } else if (a.link) {
        await linkPhoneCode(a.phone!, code);
        if (mounted) {
          toast(context, 'Phone number saved');
          context.pop(true);
        }
      } else {
        await verifyPhoneCode(a.phone!, code);
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
        await sendPhoneCode(a.phone!);
      }
      _startTimer();
      if (mounted) setState(() => _info = 'A new code is on its way.');
    } catch (e) {
      if (e is EmailAuthError && e.code == 'wait' && e.seconds != null) _startTimer(e.seconds!);
      if (e is PhoneAuthError && e.code == 'wait' && e.seconds != null) _startTimer(e.seconds!);
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
          ? 'Enter the 6-digit code we sent to ${a.email}. It can take a minute to arrive — check Spam or Promotions too.'
          : 'We sent an SMS with a 6-digit code to ${prettyPhone(a.phone!)}.',
      children: [
        TextField(
          controller: _code,
          autofocus: true,
          keyboardType: TextInputType.number,
          textAlign: TextAlign.center,
          maxLength: 6,
          autofillHints: const [AutofillHints.oneTimeCode],
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style: context.text.headlineMedium?.copyWith(letterSpacing: 10),
          decoration: InputDecoration(counterText: '', hintText: email ? '••••••' : '••••••'),
          onChanged: (v) {
            if (v.length == 6 && !a.reset) _verify();
            if (_error != null) setState(() => _error = null);
          },
          onSubmitted: (_) => _verify(),
        ),
        if (a.reset) ...[
          const SizedBox(height: 16),
          HimeField(
            controller: _newPassword,
            label: 'New password',
            obscure: true,
            prefix: const Icon(Icons.lock_outline_rounded),
            autofillHints: const [AutofillHints.newPassword],
            onSubmitted: (_) => _verify(),
          ),
        ],
        if (_error != null)
          Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: TextStyle(color: context.colors.error))),
        if (_info != null && _error == null)
          Padding(padding: const EdgeInsets.only(top: 12), child: Text(_info!, style: TextStyle(color: context.palette.muted))),
        const SizedBox(height: 24),
        PrimaryButton(label: a.reset ? 'Save new password' : 'Verify', loading: _busy, onPressed: _verify),
        const SizedBox(height: 8),
        TextButton(
          onPressed: _seconds > 0 ? null : _resend,
          child: Text(_seconds > 0 ? 'Resend code in ${_seconds}s' : 'Resend code'),
        ),
        if (!email)
          TextButton(onPressed: () => context.pop(), child: const Text('Wrong number? Change it')),
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
