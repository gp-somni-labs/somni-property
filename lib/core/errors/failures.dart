import 'package:equatable/equatable.dart';

/// Base failure class for error handling across the app
abstract class Failure extends Equatable {
  final String message;
  final int? statusCode;

  const Failure({required this.message, this.statusCode});

  @override
  List<Object?> get props => [message, statusCode];
}

/// Server-related failures
class ServerFailure extends Failure {
  const ServerFailure({required super.message, super.statusCode});
}

/// Network connectivity failures
class NetworkFailure extends Failure {
  const NetworkFailure({
    super.message = 'No internet connection. Please check your network.',
  });
}

/// VPN connection failures
class VpnFailure extends Failure {
  const VpnFailure({
    super.message =
        'Tailscale VPN not connected. Please connect to access SomniCluster.',
  });
}

/// Authentication failures
class AuthFailure extends Failure {
  const AuthFailure({required super.message, super.statusCode});
}

/// Token expiration
class TokenExpiredFailure extends AuthFailure {
  const TokenExpiredFailure({
    super.message = 'Your session has expired. Please log in again.',
    super.statusCode = 401,
  });
}

/// Invalid credentials
class InvalidCredentialsFailure extends AuthFailure {
  const InvalidCredentialsFailure({
    super.message = 'Invalid username or password.',
    super.statusCode = 401,
  });
}

/// Cache failures
class CacheFailure extends Failure {
  const CacheFailure({
    super.message = 'Failed to retrieve cached data.',
  });
}

/// File operation failures
class FileFailure extends Failure {
  const FileFailure({required super.message});
}

/// Permission denied failures
class PermissionFailure extends Failure {
  final String permissionType;

  const PermissionFailure({
    required this.permissionType,
    super.message = 'Permission denied',
  });

  @override
  List<Object?> get props => [message, permissionType];
}

/// Unknown/unexpected failures
class UnknownFailure extends Failure {
  const UnknownFailure({
    super.message = 'An unexpected error occurred. Please try again.',
  });
}
