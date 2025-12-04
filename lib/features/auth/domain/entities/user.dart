import 'package:equatable/equatable.dart';

/// User entity representing an authenticated user
class User extends Equatable {
  final String id;
  final String email;
  final String name;
  final String role;
  final String? phone;
  final String? avatarUrl;
  final List<String> groups;
  final DateTime? lastLogin;
  final bool isActive;

  const User({
    required this.id,
    required this.email,
    required this.name,
    required this.role,
    this.phone,
    this.avatarUrl,
    this.groups = const [],
    this.lastLogin,
    this.isActive = true,
  });

  bool get isTenant => role == 'tenant';
  bool get isManager => role == 'manager';
  bool get isAdmin => role == 'admin';
  bool get isViewer => role == 'viewer';

  /// Check if user can manage properties
  bool get canManageProperties => isAdmin || isManager;

  /// Check if user can manage tenants
  bool get canManageTenants => isAdmin || isManager;

  /// Check if user can view financial data
  bool get canViewFinancials => isAdmin || isManager;

  /// Check if user can submit maintenance requests
  bool get canSubmitMaintenance => isAdmin || isManager || isTenant;

  @override
  List<Object?> get props => [
        id,
        email,
        name,
        role,
        phone,
        avatarUrl,
        groups,
        lastLogin,
        isActive,
      ];
}

/// Authentication tokens
class AuthTokens extends Equatable {
  final String accessToken;
  final String refreshToken;
  final DateTime expiresAt;

  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresAt,
  });

  bool get isExpired => DateTime.now().isAfter(expiresAt);

  @override
  List<Object?> get props => [accessToken, refreshToken, expiresAt];
}

/// Login credentials
class LoginCredentials extends Equatable {
  final String username;
  final String password;
  final String? totpCode;

  const LoginCredentials({
    required this.username,
    required this.password,
    this.totpCode,
  });

  @override
  List<Object?> get props => [username, password, totpCode];
}
