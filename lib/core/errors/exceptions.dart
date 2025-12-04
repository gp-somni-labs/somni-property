/// Base exception class
class AppException implements Exception {
  final String message;
  final int? statusCode;

  const AppException({required this.message, this.statusCode});

  @override
  String toString() => 'AppException: $message (code: $statusCode)';
}

/// Server exceptions (HTTP errors)
class ServerException extends AppException {
  const ServerException({required super.message, super.statusCode});
}

/// Network exceptions (connectivity issues)
class NetworkException extends AppException {
  const NetworkException({
    super.message = 'Network error occurred',
  });
}

/// VPN connection exception
class VpnException extends AppException {
  const VpnException({
    super.message = 'Tailscale VPN is not connected',
  });
}

/// Authentication exceptions
class AuthException extends AppException {
  const AuthException({required super.message, super.statusCode});
}

/// Token expired exception
class TokenExpiredException extends AuthException {
  const TokenExpiredException({
    super.message = 'Token has expired',
    super.statusCode = 401,
  });
}

/// Invalid credentials exception
class InvalidCredentialsException extends AuthException {
  const InvalidCredentialsException({
    super.message = 'Invalid credentials',
    super.statusCode = 401,
  });
}

/// Cache exceptions
class CacheException extends AppException {
  const CacheException({
    super.message = 'Cache error occurred',
  });
}

/// File operation exceptions
class FileException extends AppException {
  const FileException({required super.message});
}

/// Permission exceptions
class PermissionException extends AppException {
  final String permissionType;

  const PermissionException({
    required this.permissionType,
    super.message = 'Permission denied',
  });
}

/// Property not found exception
class PropertyNotFoundException extends AppException {
  const PropertyNotFoundException({
    super.message = 'Property not found',
    super.statusCode = 404,
  });
}

/// Tenant not found exception
class TenantNotFoundException extends AppException {
  const TenantNotFoundException({
    super.message = 'Tenant not found',
    super.statusCode = 404,
  });
}

/// Lease not found exception
class LeaseNotFoundException extends AppException {
  const LeaseNotFoundException({
    super.message = 'Lease not found',
    super.statusCode = 404,
  });
}
