import '../../core/utils.dart';

/// Public profile of another person as the server lets us see it.
class Profile {
  Profile({
    required this.id,
    required this.displayName,
    this.username,
    this.about,
    this.avatarPath,
    this.avatarVersion = 0,
    this.isContact = false,
    this.blockedByMe = false,
  });

  final String id;
  final String displayName;
  final String? username;
  final String? about;
  final String? avatarPath;
  final int avatarVersion;
  final bool isContact;
  final bool blockedByMe;

  String get name => displayName.isNotEmpty ? displayName : (username ?? 'Hime user');

  factory Profile.fromJson(Map<String, dynamic> j) => Profile(
        id: j['id'] as String,
        displayName: (j['display_name'] as String?) ?? '',
        username: j['username'] as String?,
        about: j['about'] as String?,
        avatarPath: j['avatar_path'] as String?,
        avatarVersion: (j['avatar_version'] as num?)?.toInt() ?? 0,
        isContact: j['is_contact'] == true,
        blockedByMe: j['blocked_by_me'] == true,
      );
}

/// One row of the chat list.
class ChatSummary {
  ChatSummary({
    required this.id,
    required this.type,
    required this.title,
    this.avatarPath,
    this.avatarVersion = 0,
    this.otherUserId,
    this.communityId,
    this.isAnnouncement = false,
    this.onlyAdminsSend = false,
    this.memberCount = 0,
    this.myRole = 'member',
    this.lastMessageId,
    required this.lastAt,
    this.lastKind,
    this.lastSenderId,
    this.lastDeleted = false,
    this.lastPreview,
    this.lastEdited = false,
    this.unread = 0,
    this.mutedUntil,
    this.archived = false,
    this.pinnedAt,
    this.peerDeliveredUpTo,
    this.peerReadUpTo,
    this.blockedByMe = false,
    this.raw,
  });

  final String id;
  final String type;
  String title;
  String? avatarPath;
  int avatarVersion;
  final String? otherUserId;
  final String? communityId;
  final bool isAnnouncement;
  bool onlyAdminsSend;
  int memberCount;
  String myRole;
  String? lastMessageId;
  DateTime lastAt;
  String? lastKind;
  String? lastSenderId;
  bool lastDeleted;
  String? lastPreview;
  bool lastEdited;
  int unread;
  DateTime? mutedUntil;
  bool archived;
  DateTime? pinnedAt;
  DateTime? peerDeliveredUpTo;
  DateTime? peerReadUpTo;
  bool blockedByMe;
  final Map<String, dynamic>? raw;

  bool get isGroup => type == 'group';
  bool get isMuted => mutedUntil != null && mutedUntil!.isAfter(DateTime.now());
  bool get isAdmin => myRole == 'owner' || myRole == 'admin';
  bool get canSend => !(isGroup && (onlyAdminsSend || isAnnouncement) && !isAdmin);

  factory ChatSummary.fromRpc(Map<String, dynamic> j) => ChatSummary(
        id: j['conversation_id'] as String,
        type: j['type'] as String,
        title: (j['title'] as String?) ?? 'Chat',
        avatarPath: j['avatar_path'] as String?,
        avatarVersion: (j['avatar_version'] as num?)?.toInt() ?? 0,
        otherUserId: j['other_user_id'] as String?,
        communityId: j['community_id'] as String?,
        isAnnouncement: j['is_announcement'] == true,
        onlyAdminsSend: j['only_admins_send'] == true,
        memberCount: (j['member_count'] as num?)?.toInt() ?? 0,
        myRole: (j['my_role'] as String?) ?? 'member',
        lastMessageId: j['last_message_id'] as String?,
        lastAt: parseTime(j['last_message_at']) ?? DateTime.now().toUtc(),
        lastKind: j['last_kind'] as String?,
        lastSenderId: j['last_sender_id'] as String?,
        lastDeleted: j['last_deleted'] == true,
        lastEdited: j['last_edited'] == true,
        unread: (j['unread_count'] as num?)?.toInt() ?? 0,
        mutedUntil: parseTime(j['muted_until']),
        archived: j['archived'] == true,
        pinnedAt: parseTime(j['pinned_at']),
        peerDeliveredUpTo: parseTime(j['peer_delivered_up_to']),
        peerReadUpTo: parseTime(j['peer_read_up_to']),
        blockedByMe: j['blocked_by_me'] == true,
        raw: j,
      );
}

enum Delivery { pending, failed, sent, delivered, read }

/// A decrypted message ready for the UI.
class ChatMessage {
  ChatMessage({
    required this.id,
    required this.conversationId,
    required this.senderId,
    this.senderDeviceId,
    required this.kind,
    this.payload,
    this.system,
    required this.createdAt,
    this.editedAt,
    this.deletedAt,
    this.localState = 0,
    this.undecryptable = false,
  });

  final String id;
  final String conversationId;
  final String? senderId;
  final String? senderDeviceId;
  final String kind;
  final Map<String, dynamic>? payload;
  final Map<String, dynamic>? system;
  final DateTime createdAt;
  final DateTime? editedAt;
  final DateTime? deletedAt;
  final int localState;
  final bool undecryptable;

  bool get isDeleted => deletedAt != null;
  bool get isSystem => kind == 'system';
  bool get isCall => kind == 'call';
  String get text => (payload?['text'] as String?) ?? '';
  Map<String, dynamic>? get media => payload?['media'] as Map<String, dynamic>?;
  Map<String, dynamic>? get reply => payload?['reply'] as Map<String, dynamic>?;
  bool get forwarded => payload?['fwd'] == true;

  ChatMessage copyWith({int? localState, Map<String, dynamic>? payload, DateTime? deletedAt, DateTime? editedAt}) => ChatMessage(
        id: id,
        conversationId: conversationId,
        senderId: senderId,
        senderDeviceId: senderDeviceId,
        kind: kind,
        payload: payload ?? this.payload,
        system: system,
        createdAt: createdAt,
        editedAt: editedAt ?? this.editedAt,
        deletedAt: deletedAt ?? this.deletedAt,
        localState: localState ?? this.localState,
        undecryptable: undecryptable,
      );

  /// Short text for chat-list previews and notifications.
  String preview() {
    if (isDeleted) return 'This message was deleted';
    if (undecryptable) return 'Waiting for this message';
    if (isCall) return callLabel(system);
    if (isSystem) return systemLabel(system, null);
    return previewFor(kind, payload);
  }

  static String previewFor(String? kind, Map<String, dynamic>? payload) {
    final text = (payload?['text'] as String?) ?? '';
    switch (kind) {
      case 'image':
        return text.isEmpty ? '📷 Photo' : '📷 $text';
      case 'video':
        return text.isEmpty ? '🎥 Video' : '🎥 $text';
      case 'voice':
        return '🎤 Voice message';
      case 'audio':
        return '🎵 Audio';
      case 'document':
        return '📄 ${(payload?['media'] as Map?)?['name'] ?? 'Document'}';
      case 'contact':
        return '👤 ${(payload?['contact'] as Map?)?['name'] ?? 'Contact'}';
      case 'location':
        return '📍 Location';
      default:
        return text;
    }
  }

  static String callLabel(Map<String, dynamic>? s) {
    final video = s?['media'] == 'video';
    final status = s?['status'] as String?;
    final kind = video ? 'video call' : 'voice call';
    switch (status) {
      case 'ended':
        final secs = (s?['duration'] as num?)?.toInt() ?? 0;
        return '${video ? '🎥' : '📞'} ${kind[0].toUpperCase()}${kind.substring(1)} · ${Fmt.duration(Duration(seconds: secs))}';
      case 'declined':
        return '📵 Declined $kind';
      case 'busy':
        return '📵 $kind · busy';
      case 'failed':
        return '⚠️ $kind failed';
      case 'cancelled':
      case 'missed':
      default:
        return '📞 Missed $kind';
    }
  }

  /// Text for group events; [names] maps user ids to display names.
  static String systemLabel(Map<String, dynamic>? s, String Function(String? id)? names) {
    String n(Object? id) => names?.call(id as String?) ?? 'Someone';
    String many(Object? ids) => (ids as List? ?? const []).map((e) => n(e)).join(', ');
    switch (s?['type']) {
      case 'group_created':
        return '${n(s?['actor'])} created the group "${s?['name']}"';
      case 'community_created':
        return '${n(s?['actor'])} created the community "${s?['name']}"';
      case 'members_added':
        return '${n(s?['actor'])} added ${many(s?['targets'])}';
      case 'member_removed':
        return '${n(s?['actor'])} removed ${many(s?['targets'])}';
      case 'member_left':
        return '${n(s?['actor'])} left';
      case 'member_joined_link':
        return '${n(s?['actor'])} joined using an invite link';
      case 'member_joined_community':
        return '${n(s?['actor'])} joined from the community';
      case 'group_renamed':
        return '${n(s?['actor'])} changed the group name to "${s?['name']}"';
      case 'description_changed':
        return '${n(s?['actor'])} changed the group description';
      case 'photo_changed':
        return '${n(s?['actor'])} changed the group photo';
      case 'admin_added':
        return '${n(s?['actor'])} made ${many(s?['targets'])} an admin';
      case 'admin_removed':
        return '${n(s?['actor'])} dismissed ${many(s?['targets'])} as admin';
      case 'send_permission_changed':
        return s?['only_admins'] == true
            ? '${n(s?['actor'])} allowed only admins to send messages'
            : '${n(s?['actor'])} allowed all members to send messages';
      default:
        return 'Group updated';
    }
  }
}
