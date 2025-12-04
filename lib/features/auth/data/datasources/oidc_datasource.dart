import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:somni_property/core/config/oidc_config.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/features/auth/data/models/user_model.dart';

/// OIDC Data Source for Authelia SSO authentication
///
/// Implements the Authorization Code flow with PKCE for secure authentication
/// on web and desktop platforms.
abstract class OidcDataSource {
  /// Initiate OIDC login flow
  Future<OidcLoginResult> login({required bool isVpnConnected});

  /// Refresh the access token using refresh token
  Future<OidcTokenResult> refreshToken({
    required String refreshToken,
    required bool isVpnConnected,
  });

  /// Logout and revoke tokens
  Future<void> logout({
    required String idToken,
    required bool isVpnConnected,
  });

  /// Get user info from OIDC userinfo endpoint
  Future<OidcUserInfo> getUserInfo({
    required String accessToken,
    required bool isVpnConnected,
  });
}

/// Implementation of OIDC data source using flutter_appauth
class OidcDataSourceImpl implements OidcDataSource {
  final FlutterAppAuth _appAuth;

  OidcDataSourceImpl({FlutterAppAuth? appAuth})
      : _appAuth = appAuth ?? const FlutterAppAuth();

  @override
  Future<OidcLoginResult> login({required bool isVpnConnected}) async {
    try {
      final issuer = OidcConfig.getIssuer(isVpnConnected: isVpnConnected);
      final redirectUri = OidcConfig.getRedirectUri();

      debugPrint('OIDC: Starting login flow with issuer: $issuer');
      debugPrint('OIDC: Redirect URI: $redirectUri');

      final result = await _appAuth.authorizeAndExchangeCode(
        AuthorizationTokenRequest(
          OidcConfig.clientId,
          redirectUri,
          issuer: issuer,
          scopes: OidcConfig.scopes,
          promptValues: ['login'], // Force login prompt
          additionalParameters: {
            'response_mode': 'query', // Authelia prefers query for web/desktop
          },
        ),
      );

      if (result == null) {
        throw const AuthException(
          message: 'OIDC login was cancelled or failed',
          statusCode: 401,
        );
      }

      debugPrint('OIDC: Login successful, parsing tokens');

      // Parse the ID token to get user claims
      final idToken = result.idToken;
      if (idToken == null) {
        throw const AuthException(
          message: 'No ID token received from OIDC provider',
          statusCode: 401,
        );
      }

      final claims = _parseIdToken(idToken);
      final userInfo = OidcUserInfo.fromClaims(claims);

      // Check if user has app access
      if (!OidcRoleMapper.hasAppAccess(userInfo.groups)) {
        throw const AuthException(
          message: 'You do not have permission to access this application',
          statusCode: 403,
        );
      }

      return OidcLoginResult(
        accessToken: result.accessToken!,
        refreshToken: result.refreshToken,
        idToken: idToken,
        expiresAt: result.accessTokenExpirationDateTime ??
            DateTime.now().add(const Duration(hours: 1)),
        userInfo: userInfo,
      );
    } on AuthException {
      rethrow;
    } catch (e) {
      debugPrint('OIDC: Login error: $e');
      throw AuthException(
        message: 'OIDC login failed: ${e.toString()}',
        statusCode: 401,
      );
    }
  }

  @override
  Future<OidcTokenResult> refreshToken({
    required String refreshToken,
    required bool isVpnConnected,
  }) async {
    try {
      final issuer = OidcConfig.getIssuer(isVpnConnected: isVpnConnected);

      debugPrint('OIDC: Refreshing token with issuer: $issuer');

      final result = await _appAuth.token(
        TokenRequest(
          OidcConfig.clientId,
          OidcConfig.getRedirectUri(),
          issuer: issuer,
          refreshToken: refreshToken,
          scopes: OidcConfig.scopes,
        ),
      );

      if (result == null) {
        throw const TokenExpiredException();
      }

      return OidcTokenResult(
        accessToken: result.accessToken!,
        refreshToken: result.refreshToken ?? refreshToken,
        idToken: result.idToken,
        expiresAt: result.accessTokenExpirationDateTime ??
            DateTime.now().add(const Duration(hours: 1)),
      );
    } catch (e) {
      debugPrint('OIDC: Token refresh error: $e');
      throw const TokenExpiredException();
    }
  }

  @override
  Future<void> logout({
    required String idToken,
    required bool isVpnConnected,
  }) async {
    try {
      final issuer = OidcConfig.getIssuer(isVpnConnected: isVpnConnected);
      final postLogoutRedirect = OidcConfig.getPostLogoutRedirectUri();

      debugPrint('OIDC: Logging out with issuer: $issuer');

      // End session request for OIDC logout
      await _appAuth.endSession(
        EndSessionRequest(
          idTokenHint: idToken,
          postLogoutRedirectUrl: postLogoutRedirect,
          issuer: issuer,
        ),
      );

      debugPrint('OIDC: Logout successful');
    } catch (e) {
      // Logout errors are not critical - we still clear local tokens
      debugPrint('OIDC: Logout warning: $e');
    }
  }

  @override
  Future<OidcUserInfo> getUserInfo({
    required String accessToken,
    required bool isVpnConnected,
  }) async {
    // Note: For now, we parse user info from the ID token claims
    // If more detailed info is needed, implement a call to the userinfo endpoint
    throw UnimplementedError(
      'Use ID token claims instead. Userinfo endpoint call not implemented.',
    );
  }

  /// Parse JWT ID token to extract claims
  Map<String, dynamic> _parseIdToken(String idToken) {
    try {
      // JWT format: header.payload.signature
      final parts = idToken.split('.');
      if (parts.length != 3) {
        throw const AuthException(
          message: 'Invalid ID token format',
          statusCode: 401,
        );
      }

      // Decode the payload (second part)
      final payload = parts[1];
      // Add padding if needed for base64 decoding
      final normalized = base64Url.normalize(payload);
      final decoded = utf8.decode(base64Url.decode(normalized));

      return jsonDecode(decoded) as Map<String, dynamic>;
    } catch (e) {
      debugPrint('OIDC: Failed to parse ID token: $e');
      throw const AuthException(
        message: 'Failed to parse authentication token',
        statusCode: 401,
      );
    }
  }
}

/// Result of OIDC login containing tokens and user info
class OidcLoginResult {
  final String accessToken;
  final String? refreshToken;
  final String idToken;
  final DateTime expiresAt;
  final OidcUserInfo userInfo;

  const OidcLoginResult({
    required this.accessToken,
    this.refreshToken,
    required this.idToken,
    required this.expiresAt,
    required this.userInfo,
  });

  /// Convert to AuthTokensModel for storage
  AuthTokensModel toTokensModel() {
    return AuthTokensModel(
      accessToken: accessToken,
      refreshToken: refreshToken ?? '',
      expiresAt: expiresAt,
    );
  }

  /// Convert to UserModel for app use
  UserModel toUserModel() {
    return userInfo.toUserModel();
  }
}

/// Result of token refresh
class OidcTokenResult {
  final String accessToken;
  final String refreshToken;
  final String? idToken;
  final DateTime expiresAt;

  const OidcTokenResult({
    required this.accessToken,
    required this.refreshToken,
    this.idToken,
    required this.expiresAt,
  });

  /// Convert to AuthTokensModel for storage
  AuthTokensModel toTokensModel() {
    return AuthTokensModel(
      accessToken: accessToken,
      refreshToken: refreshToken,
      expiresAt: expiresAt,
    );
  }
}

/// User information parsed from OIDC claims
class OidcUserInfo {
  final String sub; // Subject - unique user identifier (username in LLDAP)
  final String email;
  final String name;
  final List<String> groups;
  final String? preferredUsername;

  const OidcUserInfo({
    required this.sub,
    required this.email,
    required this.name,
    required this.groups,
    this.preferredUsername,
  });

  /// Parse from ID token claims
  factory OidcUserInfo.fromClaims(Map<String, dynamic> claims) {
    // Parse groups - Authelia returns as array
    List<String> groups = [];
    if (claims['groups'] != null) {
      if (claims['groups'] is List) {
        groups = (claims['groups'] as List).cast<String>();
      } else if (claims['groups'] is String) {
        groups = [claims['groups'] as String];
      }
    }

    return OidcUserInfo(
      sub: claims['sub'] as String? ?? '',
      email: claims['email'] as String? ?? '',
      name: claims['name'] as String? ??
          claims['preferred_username'] as String? ??
          claims['sub'] as String? ??
          '',
      groups: groups,
      preferredUsername: claims['preferred_username'] as String?,
    );
  }

  /// Get the application role based on LDAP groups
  String get role => OidcRoleMapper.mapGroupsToRole(groups);

  /// Convert to UserModel for app use
  UserModel toUserModel() {
    return UserModel(
      id: sub,
      email: email,
      name: name,
      role: role,
      groups: groups,
      isActive: true,
    );
  }
}
