import 'dart:async';
import 'dart:convert';

import 'package:crypto/crypto.dart' as crypto;
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart' show StringCharacters;
import 'package:intl/intl.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Time and size formatting used across the app.
class Fmt {
  static String chatTime(DateTime t) {
    final local = t.toLocal();
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final day = DateTime(local.year, local.month, local.day);
    final diff = today.difference(day).inDays;
    if (diff == 0) return DateFormat.jm().format(local);
    if (diff == 1) return 'Yesterday';
    if (diff < 7) return DateFormat.E().format(local);
    return DateFormat('dd/MM/yy').format(local);
  }

  static String time(DateTime t) => DateFormat.jm().format(t.toLocal());

  static String dayLabel(DateTime t) {
    final local = t.toLocal();
    final now = DateTime.now();
    final diff = DateTime(now.year, now.month, now.day).difference(DateTime(local.year, local.month, local.day)).inDays;
    if (diff == 0) return 'Today';
    if (diff == 1) return 'Yesterday';
    if (diff < 7) return DateFormat.EEEE().format(local);
    return DateFormat.yMMMMd().format(local);
  }

  static String lastSeen(DateTime? t) {
    if (t == null) return '';
    final local = t.toLocal();
    final now = DateTime.now();
    final diff = now.difference(local);
    if (diff.inMinutes < 1) return 'last seen just now';
    if (diff.inMinutes < 60) return 'last seen ${diff.inMinutes} min ago';
    final dayDiff = DateTime(now.year, now.month, now.day)
        .difference(DateTime(local.year, local.month, local.day))
        .inDays;
    if (dayDiff == 0) return 'last seen today at ${DateFormat.jm().format(local)}';
    if (dayDiff == 1) return 'last seen yesterday at ${DateFormat.jm().format(local)}';
    return 'last seen ${DateFormat('d MMM').format(local)} at ${DateFormat.jm().format(local)}';
  }

  static String duration(Duration d) {
    final h = d.inHours;
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return h > 0 ? '$h:$m:$s' : '$m:$s';
  }

  static String bytes(int b) {
    if (b < 1024) return '$b B';
    if (b < 1024 * 1024) return '${(b / 1024).toStringAsFixed(0)} KB';
    if (b < 1024 * 1024 * 1024) return '${(b / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(b / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
  }

  static String initials(String name) {
    final parts = name.trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first.characters.first.toUpperCase();
    return (parts.first.characters.first + parts.last.characters.first).toUpperCase();
  }
}

class Validators {
  static final _email = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$');
  static final _username = RegExp(r'^[a-z0-9_.]{3,24}$');

  static String? email(String? v) {
    final s = (v ?? '').trim();
    if (s.isEmpty) return 'Enter your email';
    if (!_email.hasMatch(s)) return 'Enter a valid email address';
    return null;
  }

  static String? password(String? v) {
    final s = v ?? '';
    if (s.length < 8) return 'Use at least 8 characters';
    if (!RegExp(r'[A-Za-z]').hasMatch(s) || !RegExp(r'[0-9]').hasMatch(s)) {
      return 'Use letters and numbers';
    }
    return null;
  }

  static String? required(String? v, [String label = 'This field']) =>
      (v ?? '').trim().isEmpty ? '$label is required' : null;

  static String? username(String? v) {
    final s = (v ?? '').trim().toLowerCase();
    if (s.length < 3) return 'At least 3 characters';
    if (!_username.hasMatch(s)) return 'Use a–z, 0–9, dot or underscore';
    return null;
  }
}

/// Phone number helpers. Numbers are normalised to E.164 and hashed with
/// SHA-256 before contact discovery so raw address books never leave the phone.
class Phone {
  static String digits(String s) => s.replaceAll(RegExp(r'\D'), '');

  static String? toE164(String raw, String dialCode) {
    var s = raw.trim();
    if (s.isEmpty) return null;
    if (s.startsWith('+')) {
      final d = digits(s);
      return d.length >= 8 ? '+$d' : null;
    }
    var d = digits(s);
    if (d.startsWith('00')) return '+${d.substring(2)}';
    d = d.replaceFirst(RegExp(r'^0+'), '');
    final cc = digits(dialCode);
    if (d.length < 6) return null;
    if (d.startsWith(cc) && d.length > 10) return '+$d';
    return '+$cc$d';
  }

  static String hash(String e164) => crypto.sha256.convert(utf8.encode('+${digits(e164)}')).toString();
}

/// Errors whose toString() is written for people and safe to show as-is.
abstract class UserFacingException implements Exception {}

/// Turns backend exceptions into short, human messages.
String friendlyError(Object e) {
  if (e is UserFacingException) return e.toString();
  if (e is StateError) return e.message;
  if (e is AuthException) {
    final m = e.message.toLowerCase();
    if (m.contains('invalid login') || m.contains('invalid credentials')) return 'Incorrect email or password.';
    if (m.contains('email not confirmed')) return 'Please verify your email first. Check your inbox.';
    if (m.contains('already registered') || m.contains('already been registered')) return 'An account with this email already exists.';
    if (m.contains('rate limit') || m.contains('too many')) return 'Too many attempts. Please wait a minute and try again.';
    if (m.contains('phone') && (m.contains('provider') || m.contains('unsupported') || m.contains('disabled'))) {
      return 'Phone sign-in isn\'t enabled on this Hime server yet. Use email for now.';
    }
    if (m.contains('token has expired') || m.contains('invalid otp') || m.contains('otp')) return 'That code is wrong or has expired.';
    if (m.contains('weak password')) return 'Choose a stronger password.';
    return e.message;
  }
  if (e is PostgrestException) {
    final m = e.message;
    const known = {
      'stale_devices': 'Security keys changed. Retrying…',
      'not_a_member': 'You are no longer a member of this chat.',
      'only_admins_can_send': 'Only admins can send messages here.',
      'you_blocked_this_contact': 'Unblock this contact to send messages.',
      'rate_limited': 'You are sending too fast. Slow down a little.',
      'edit_window_expired': 'Messages can only be edited for 15 minutes.',
      'delete_window_expired': 'This message is too old to delete for everyone.',
      'cannot_call': 'You can\'t call this person.',
      'already_in_call': 'You are already in a call.',
      'invite_invalid': 'This invite link is invalid or was reset.',
      'group_full': 'This group is full.',
      'not_allowed': 'You don\'t have permission to do that.',
      'pin_limit_reached': 'You can pin up to 3 messages.',
      'only_admins_can_pin': 'Only admins can pin messages here.',
      'only_admins_can_add': 'Only admins can add members.',
      'user_not_found': 'That account no longer exists.',
    };
    for (final entry in known.entries) {
      if (m.contains(entry.key)) return entry.value;
    }
    if (m.contains('duplicate key') && m.contains('username')) return 'That username is taken.';
    return 'Something went wrong. Please try again.';
  }
  if (e is FunctionException) {
    final details = e.details;
    if (details is Map && details['error'] == 'mfa_required') return 'Verify with two-step verification first.';
    return 'The server could not complete that request.';
  }
  if (e is TimeoutException) return 'The network is slow. Please try again.';
  final s = e.toString();
  if (s.contains('SocketException') || s.contains('ClientException') || s.contains('Failed host lookup')) {
    return 'You\'re offline. Check your connection.';
  }
  if (kDebugMode) return s;
  return 'Something went wrong. Please try again.';
}

/// Debounces rapid calls (search boxes, typing indicators).
class Debouncer {
  Debouncer(this.delay);
  final Duration delay;
  Timer? _timer;
  void call(VoidCallback action) {
    _timer?.cancel();
    _timer = Timer(delay, action);
  }

  void dispose() => _timer?.cancel();
}

DateTime? parseTime(dynamic v) {
  if (v == null) return null;
  if (v is DateTime) return v;
  if (v is int) return DateTime.fromMillisecondsSinceEpoch(v, isUtc: true);
  return DateTime.tryParse(v.toString());
}

final _urlRegex = RegExp(r'((https?:\/\/)|(www\.))[^\s<>"]+', caseSensitive: false);

List<String> findUrls(String text) => _urlRegex.allMatches(text).map((m) => m.group(0)!).toList();

RegExp get urlRegex => _urlRegex;
