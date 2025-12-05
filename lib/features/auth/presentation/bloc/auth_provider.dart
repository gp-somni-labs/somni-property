import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/core/network/network_info.dart';
import 'package:somni_property/features/auth/data/datasources/auth_local_datasource.dart';
import 'package:somni_property/features/auth/data/datasources/auth_remote_datasource.dart';
import 'package:somni_property/features/auth/data/datasources/oidc_datasource.dart';
import 'package:somni_property/features/auth/data/repositories/auth_repository_impl.dart';
import 'package:somni_property/features/auth/domain/entities/user.dart';
import 'package:somni_property/features/auth/domain/repositories/auth_repository.dart';

/// Provider for FlutterSecureStorage
final secureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
        accessibility: KeychainAccessibility.first_unlock_this_device),
  );
});

/// Provider for AuthLocalDataSource
final authLocalDataSourceProvider = Provider<AuthLocalDataSource>((ref) {
  return AuthLocalDataSourceImpl(
    secureStorage: ref.watch(secureStorageProvider),
  );
});

/// Provider for AuthRemoteDataSource
final authRemoteDataSourceProvider = Provider<AuthRemoteDataSource>((ref) {
  return AuthRemoteDataSourceImpl(
    apiClient: ref.watch(apiClientProvider),
  );
});

/// Provider for AuthRepository
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepositoryImpl(
    remoteDataSource: ref.watch(authRemoteDataSourceProvider),
    localDataSource: ref.watch(authLocalDataSourceProvider),
    networkInfo: ref.watch(networkInfoProvider),
  );
});

/// Provider for OIDC DataSource
/// Uses platform-specific implementation (web uses redirect flow, native uses flutter_appauth)
final oidcDataSourceProvider = Provider<OidcDataSource>((ref) {
  return createOidcDataSource();
});

/// Auth state notifier
class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository repository;
  final OidcDataSource oidcDataSource;
  final AuthLocalDataSource localDataSource;
  final NetworkInfo networkInfo;

  // Store OIDC tokens for logout
  String? _idToken;

  AuthNotifier({
    required this.repository,
    required this.oidcDataSource,
    required this.localDataSource,
    required this.networkInfo,
  }) : super(const AuthState.initial());

  Future<void> checkAuthStatus() async {
    state = const AuthState.loading();

    final isAuthenticated = await repository.isAuthenticated();
    if (isAuthenticated) {
      final result = await repository.getCurrentUser();
      result.fold(
        (failure) => state = const AuthState.unauthenticated(),
        (user) => state = AuthState.authenticated(user),
      );
    } else {
      state = const AuthState.unauthenticated();
    }
  }

  /// Login with username/password (fallback method)
  Future<void> login(LoginCredentials credentials) async {
    state = const AuthState.loading();

    final result = await repository.login(credentials);
    result.fold(
      (failure) => state = AuthState.error(failure.message),
      (user) => state = AuthState.authenticated(user),
    );
  }

  /// Login with OIDC/SSO via Authelia
  Future<void> loginWithOidc() async {
    state = const AuthState.loading();

    try {
      // Check VPN status for correct issuer
      final isVpnConnected = await networkInfo.isVpnConnected;
      debugPrint('AuthNotifier: Starting OIDC login, VPN connected: $isVpnConnected');

      // Initiate OIDC login flow
      final result = await oidcDataSource.login(isVpnConnected: isVpnConnected);

      // Store ID token for logout
      _idToken = result.idToken;

      // Cache tokens and user info
      await localDataSource.cacheTokens(result.toTokensModel());
      await localDataSource.cacheUser(result.toUserModel());

      debugPrint('AuthNotifier: OIDC login successful for ${result.userInfo.name}');

      state = AuthState.authenticated(result.toUserModel().toEntity());
    } catch (e) {
      debugPrint('AuthNotifier: OIDC login failed: $e');
      state = AuthState.error(e.toString());
    }
  }

  Future<void> logout() async {
    state = const AuthState.loading();

    try {
      // Try OIDC logout if we have an ID token
      if (_idToken != null) {
        final isVpnConnected = await networkInfo.isVpnConnected;
        await oidcDataSource.logout(
          idToken: _idToken!,
          isVpnConnected: isVpnConnected,
        );
        _idToken = null;
      }
    } catch (e) {
      // OIDC logout errors are non-critical
      debugPrint('AuthNotifier: OIDC logout warning: $e');
    }

    // Always clear local state and call repository logout
    final result = await repository.logout();
    result.fold(
      (failure) => state = AuthState.error(failure.message),
      (_) => state = const AuthState.unauthenticated(),
    );
  }

  Future<void> verifyTwoFactor(String code) async {
    state = const AuthState.loading();

    final result = await repository.verifyTwoFactor(code);
    result.fold(
      (failure) => state = AuthState.error(failure.message),
      (verified) {
        if (verified) {
          checkAuthStatus();
        } else {
          state = const AuthState.error('Invalid verification code');
        }
      },
    );
  }
}

/// Auth state
sealed class AuthState {
  const AuthState();

  const factory AuthState.initial() = AuthStateInitial;
  const factory AuthState.loading() = AuthStateLoading;
  const factory AuthState.authenticated(User user) = AuthStateAuthenticated;
  const factory AuthState.unauthenticated() = AuthStateUnauthenticated;
  const factory AuthState.error(String message) = AuthStateError;
  const factory AuthState.requiresTwoFactor() = AuthStateRequiresTwoFactor;

  /// Get the user if authenticated, null otherwise
  User? get user {
    if (this is AuthStateAuthenticated) {
      return (this as AuthStateAuthenticated).user;
    }
    return null;
  }
}

class AuthStateInitial extends AuthState {
  const AuthStateInitial();
}

class AuthStateLoading extends AuthState {
  const AuthStateLoading();
}

class AuthStateAuthenticated extends AuthState {
  final User user;
  const AuthStateAuthenticated(this.user);
}

class AuthStateUnauthenticated extends AuthState {
  const AuthStateUnauthenticated();
}

class AuthStateError extends AuthState {
  final String message;
  const AuthStateError(this.message);
}

class AuthStateRequiresTwoFactor extends AuthState {
  const AuthStateRequiresTwoFactor();
}

/// Provider for AuthNotifier
final authNotifierProvider =
    StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    repository: ref.watch(authRepositoryProvider),
    oidcDataSource: ref.watch(oidcDataSourceProvider),
    localDataSource: ref.watch(authLocalDataSourceProvider),
    networkInfo: ref.watch(networkInfoProvider),
  );
});

/// Convenience provider for checking if user is authenticated
final isAuthenticatedProvider = Provider<bool>((ref) {
  final authState = ref.watch(authNotifierProvider);
  return authState is AuthStateAuthenticated;
});

/// Provider for current user
final currentUserProvider = Provider<User?>((ref) {
  final authState = ref.watch(authNotifierProvider);
  if (authState is AuthStateAuthenticated) {
    return authState.user;
  }
  return null;
});
