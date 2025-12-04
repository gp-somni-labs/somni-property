import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/auth/domain/entities/user.dart';

/// Abstract repository for authentication operations
abstract class AuthRepository {
  /// Login with credentials
  Future<Either<Failure, User>> login(LoginCredentials credentials);

  /// Logout current user
  Future<Either<Failure, void>> logout();

  /// Get current authenticated user
  Future<Either<Failure, User>> getCurrentUser();

  /// Check if user is authenticated
  Future<bool> isAuthenticated();

  /// Refresh authentication token
  Future<Either<Failure, AuthTokens>> refreshToken();

  /// Verify two-factor authentication code
  Future<Either<Failure, bool>> verifyTwoFactor(String code);
}
