import 'package:somni_property/features/auth/domain/entities/user.dart';

/// User model for JSON serialization
class UserModel extends User {
  const UserModel({
    required super.id,
    required super.email,
    required super.name,
    required super.role,
    super.phone,
    super.avatarUrl,
    super.groups,
    super.lastLogin,
    super.isActive,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id']?.toString() ?? '',
      email: json['email'] as String? ?? '',
      name: json['name'] as String? ??
          json['full_name'] as String? ??
          json['display_name'] as String? ??
          '',
      role: json['role'] as String? ?? 'viewer',
      phone: json['phone'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      groups: (json['groups'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      lastLogin: json['last_login'] != null
          ? DateTime.tryParse(json['last_login'] as String)
          : null,
      isActive: json['is_active'] as bool? ?? true,
    );
  }

  /// Create UserModel from login response when user data is not nested
  factory UserModel.fromLoginResponse(Map<String, dynamic> json) {
    // Extract user info that might be at root level or in claims
    return UserModel(
      id: json['user_id']?.toString() ??
          json['sub']?.toString() ??
          '',
      email: json['email'] as String? ?? '',
      name: json['name'] as String? ?? json['username'] as String? ?? '',
      role: json['role'] as String? ?? 'viewer',
      phone: json['phone'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      groups: const [],
      isActive: true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'name': name,
      'role': role,
      'phone': phone,
      'avatar_url': avatarUrl,
      'groups': groups,
      'last_login': lastLogin?.toIso8601String(),
      'is_active': isActive,
    };
  }

  User toEntity() {
    return User(
      id: id,
      email: email,
      name: name,
      role: role,
      phone: phone,
      avatarUrl: avatarUrl,
      groups: groups,
      lastLogin: lastLogin,
      isActive: isActive,
    );
  }
}

/// Auth tokens model for JSON serialization
class AuthTokensModel extends AuthTokens {
  const AuthTokensModel({
    required super.accessToken,
    required super.refreshToken,
    required super.expiresAt,
  });

  factory AuthTokensModel.fromJson(Map<String, dynamic> json) {
    // Backend returns expires_in (seconds) not expires_at
    DateTime expiresAt;
    if (json['expires_at'] != null) {
      expiresAt = DateTime.tryParse(json['expires_at'] as String) ??
          DateTime.now().add(const Duration(hours: 24));
    } else if (json['expires_in'] != null) {
      final expiresIn = json['expires_in'] as int;
      expiresAt = DateTime.now().add(Duration(seconds: expiresIn));
    } else {
      // Default to 24 hours
      expiresAt = DateTime.now().add(const Duration(hours: 24));
    }

    return AuthTokensModel(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String? ?? '',
      expiresAt: expiresAt,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'access_token': accessToken,
      'refresh_token': refreshToken,
      'expires_at': expiresAt.toIso8601String(),
    };
  }
}

/// Login response containing user and tokens
/// Backend returns: { access_token, refresh_token, token_type, expires_in, user: {...} }
class LoginResponse {
  final UserModel user;
  final AuthTokensModel tokens;

  const LoginResponse({
    required this.user,
    required this.tokens,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    // The backend returns user info nested in 'user' key
    // and tokens at root level
    final userJson = json['user'] as Map<String, dynamic>?;

    return LoginResponse(
      user: userJson != null
          ? UserModel.fromJson(userJson)
          : UserModel.fromLoginResponse(json),
      tokens: AuthTokensModel.fromJson(json),
    );
  }
}
