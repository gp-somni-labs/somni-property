// ignore: avoid_web_libraries_in_flutter
import 'dart:convert';
import 'dart:html' as html;
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:somni_property/core/config/oidc_config.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/features/auth/data/datasources/oidc_datasource.dart';
import 'package:somni_property/features/auth/data/models/user_model.dart';
import 'package:http/http.dart' as http;
import 'dart:typed_data';

/// Web-specific OIDC implementation using browser redirect flow
///
/// This implementation doesn't use flutter_appauth since it's not supported on web.
/// Instead, it uses the standard OAuth2 Authorization Code flow with PKCE:
/// 1. Generate PKCE code verifier and challenge
/// 2. Redirect user to Authelia authorization endpoint
/// 3. Handle callback with authorization code
/// 4. Exchange code for tokens via HTTP POST
class OidcDataSourceWeb implements OidcDataSource {
  // Storage keys for PKCE and state
  static const _stateKey = 'oidc_state';
  static const _codeVerifierKey = 'oidc_code_verifier';
  static const _nonceKey = 'oidc_nonce';

  @override
  Future<OidcLoginResult> login({required bool isVpnConnected}) async {
    // Check if we're handling a callback (have auth code in URL)
    final uri = Uri.parse(html.window.location.href);
    final code = uri.queryParameters['code'];
    final state = uri.queryParameters['state'];
    final error = uri.queryParameters['error'];

    if (error != null) {
      final errorDesc = uri.queryParameters['error_description'] ?? error;
      throw AuthException(message: 'OIDC error: $errorDesc', statusCode: 401);
    }

    if (code != null && state != null) {
      // We have an auth code - exchange it for tokens
      return _handleCallback(code, state);
    }

    // No code - initiate login by redirecting to Authelia
    await _initiateLogin();

    // This won't actually return - the browser will redirect
    // But we need to throw to prevent the app from continuing
    throw const AuthException(
      message: 'Redirecting to login...',
      statusCode: 302,
    );
  }

  /// Initiate OIDC login by redirecting to Authelia
  Future<void> _initiateLogin() async {
    final zone = OidcConfig.detectAccessZone();
    final issuer = OidcConfig.getIssuerForZone(zone);
    final redirectUri = OidcConfig.getRedirectUriForZone(zone);

    debugPrint('OIDC Web: Initiating login with issuer: $issuer');
    debugPrint('OIDC Web: Redirect URI: $redirectUri');

    // Generate PKCE code verifier and challenge
    final codeVerifier = _generateCodeVerifier();
    final codeChallenge = _generateCodeChallenge(codeVerifier);

    // Generate state and nonce
    final state = _generateRandomString(32);
    final nonce = _generateRandomString(32);

    // Store for callback verification
    html.window.sessionStorage[_stateKey] = state;
    html.window.sessionStorage[_codeVerifierKey] = codeVerifier;
    html.window.sessionStorage[_nonceKey] = nonce;

    // Build authorization URL
    final authUrl = Uri.parse(OidcConfig.authorizationEndpoint(issuer)).replace(
      queryParameters: {
        'client_id': OidcConfig.clientId,
        'redirect_uri': redirectUri,
        'response_type': 'code',
        'scope': OidcConfig.scopes.join(' '),
        'state': state,
        'nonce': nonce,
        'code_challenge': codeChallenge,
        'code_challenge_method': 'S256',
        'response_mode': 'query',
      },
    );

    debugPrint('OIDC Web: Redirecting to: $authUrl');

    // Redirect to Authelia
    html.window.location.href = authUrl.toString();
  }

  /// Handle the callback from Authelia with authorization code
  Future<OidcLoginResult> _handleCallback(String code, String state) async {
    debugPrint('OIDC Web: Handling callback with code');

    // Verify state
    final storedState = html.window.sessionStorage[_stateKey];
    if (storedState != state) {
      throw const AuthException(
        message: 'Invalid state parameter - possible CSRF attack',
        statusCode: 401,
      );
    }

    // Get stored code verifier
    final codeVerifier = html.window.sessionStorage[_codeVerifierKey];
    if (codeVerifier == null) {
      throw const AuthException(
        message: 'Missing code verifier - login flow corrupted',
        statusCode: 401,
      );
    }

    // Clean up stored values
    html.window.sessionStorage.remove(_stateKey);
    html.window.sessionStorage.remove(_codeVerifierKey);
    html.window.sessionStorage.remove(_nonceKey);

    // Clean up URL (remove code and state from address bar)
    final cleanUrl = Uri.parse(html.window.location.href).replace(
      queryParameters: {},
      fragment: '',
    );
    html.window.history.replaceState(null, '', cleanUrl.toString().split('?')[0]);

    // Exchange code for tokens
    final zone = OidcConfig.detectAccessZone();
    final issuer = OidcConfig.getIssuerForZone(zone);
    final redirectUri = OidcConfig.getRedirectUriForZone(zone);
    final tokenEndpoint = OidcConfig.tokenEndpoint(issuer);

    debugPrint('OIDC Web: Exchanging code at: $tokenEndpoint');

    final response = await http.post(
      Uri.parse(tokenEndpoint),
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: {
        'grant_type': 'authorization_code',
        'client_id': OidcConfig.clientId,
        'code': code,
        'redirect_uri': redirectUri,
        'code_verifier': codeVerifier,
      },
    );

    if (response.statusCode != 200) {
      debugPrint('OIDC Web: Token exchange failed: ${response.body}');
      throw AuthException(
        message: 'Token exchange failed: ${response.reasonPhrase}',
        statusCode: response.statusCode,
      );
    }

    final tokenData = jsonDecode(response.body) as Map<String, dynamic>;

    final accessToken = tokenData['access_token'] as String?;
    final idToken = tokenData['id_token'] as String?;
    final refreshToken = tokenData['refresh_token'] as String?;
    final expiresIn = tokenData['expires_in'] as int? ?? 3600;

    if (accessToken == null || idToken == null) {
      throw const AuthException(
        message: 'Invalid token response - missing tokens',
        statusCode: 401,
      );
    }

    // Parse ID token to get user claims
    final claims = _parseIdToken(idToken);
    final userInfo = OidcUserInfo.fromClaims(claims);

    // Check if user has app access
    if (!OidcRoleMapper.hasAppAccess(userInfo.groups)) {
      throw const AuthException(
        message: 'You do not have permission to access this application',
        statusCode: 403,
      );
    }

    debugPrint('OIDC Web: Login successful for ${userInfo.name}');

    return OidcLoginResult(
      accessToken: accessToken,
      refreshToken: refreshToken,
      idToken: idToken,
      expiresAt: DateTime.now().add(Duration(seconds: expiresIn)),
      userInfo: userInfo,
    );
  }

  @override
  Future<OidcTokenResult> refreshToken({
    required String refreshToken,
    required bool isVpnConnected,
  }) async {
    final zone = OidcConfig.detectAccessZone();
    final issuer = OidcConfig.getIssuerForZone(zone);
    final tokenEndpoint = OidcConfig.tokenEndpoint(issuer);

    debugPrint('OIDC Web: Refreshing token');

    final response = await http.post(
      Uri.parse(tokenEndpoint),
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: {
        'grant_type': 'refresh_token',
        'client_id': OidcConfig.clientId,
        'refresh_token': refreshToken,
      },
    );

    if (response.statusCode != 200) {
      debugPrint('OIDC Web: Token refresh failed');
      throw const TokenExpiredException();
    }

    final tokenData = jsonDecode(response.body) as Map<String, dynamic>;

    return OidcTokenResult(
      accessToken: tokenData['access_token'] as String,
      refreshToken: tokenData['refresh_token'] as String? ?? refreshToken,
      idToken: tokenData['id_token'] as String?,
      expiresAt: DateTime.now().add(
        Duration(seconds: tokenData['expires_in'] as int? ?? 3600),
      ),
    );
  }

  @override
  Future<void> logout({
    required String idToken,
    required bool isVpnConnected,
  }) async {
    final zone = OidcConfig.detectAccessZone();
    final issuer = OidcConfig.getIssuerForZone(zone);
    final postLogoutRedirect = OidcConfig.getPostLogoutRedirectUriForZone(zone);
    final endSessionUrl = OidcConfig.endSessionEndpoint(issuer);

    debugPrint('OIDC Web: Logging out');

    // Redirect to Authelia logout endpoint
    final logoutUrl = Uri.parse(endSessionUrl).replace(
      queryParameters: {
        'id_token_hint': idToken,
        'post_logout_redirect_uri': postLogoutRedirect,
      },
    );

    html.window.location.href = logoutUrl.toString();
  }

  @override
  Future<OidcUserInfo> getUserInfo({
    required String accessToken,
    required bool isVpnConnected,
  }) async {
    final zone = OidcConfig.detectAccessZone();
    final issuer = OidcConfig.getIssuerForZone(zone);
    final userinfoEndpoint = OidcConfig.userinfoEndpoint(issuer);

    final response = await http.get(
      Uri.parse(userinfoEndpoint),
      headers: {
        'Authorization': 'Bearer $accessToken',
      },
    );

    if (response.statusCode != 200) {
      throw const AuthException(
        message: 'Failed to get user info',
        statusCode: 401,
      );
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return OidcUserInfo.fromClaims(data);
  }

  /// Generate a random code verifier for PKCE
  String _generateCodeVerifier() {
    return _generateRandomString(64);
  }

  /// Generate SHA256 code challenge from verifier
  String _generateCodeChallenge(String verifier) {
    // Use SubtleCrypto for SHA256 on web
    final bytes = utf8.encode(verifier);
    final digest = _sha256(Uint8List.fromList(bytes));
    return base64UrlEncode(digest).replaceAll('=', '');
  }

  /// Simple SHA256 implementation for web
  /// Uses a basic implementation since dart:crypto isn't available
  Uint8List _sha256(Uint8List data) {
    // For web, we use a pure Dart SHA256 implementation
    // This is a simplified version - in production you'd use crypto package
    return _sha256Digest(data);
  }

  /// Generate a random string of specified length
  String _generateRandomString(int length) {
    const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    final random = Random.secure();
    return List.generate(length, (_) => charset[random.nextInt(charset.length)]).join();
  }

  /// Parse JWT ID token to extract claims
  Map<String, dynamic> _parseIdToken(String idToken) {
    try {
      final parts = idToken.split('.');
      if (parts.length != 3) {
        throw const AuthException(
          message: 'Invalid ID token format',
          statusCode: 401,
        );
      }

      final payload = parts[1];
      final normalized = base64Url.normalize(payload);
      final decoded = utf8.decode(base64Url.decode(normalized));

      return jsonDecode(decoded) as Map<String, dynamic>;
    } catch (e) {
      debugPrint('OIDC Web: Failed to parse ID token: $e');
      throw const AuthException(
        message: 'Failed to parse authentication token',
        statusCode: 401,
      );
    }
  }
}

/// Pure Dart SHA256 implementation for PKCE code challenge
/// Simplified implementation for web platform
Uint8List _sha256Digest(Uint8List data) {
  // SHA256 constants
  final k = <int>[
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ];

  // Initial hash values
  var h0 = 0x6a09e667;
  var h1 = 0xbb67ae85;
  var h2 = 0x3c6ef372;
  var h3 = 0xa54ff53a;
  var h4 = 0x510e527f;
  var h5 = 0x9b05688c;
  var h6 = 0x1f83d9ab;
  var h7 = 0x5be0cd19;

  // Pre-processing: adding padding bits
  final bitLength = data.length * 8;
  final paddedData = <int>[...data, 0x80];
  while ((paddedData.length % 64) != 56) {
    paddedData.add(0);
  }

  // Append original length in bits as 64-bit big-endian
  for (var i = 56; i >= 0; i -= 8) {
    paddedData.add((bitLength >> i) & 0xff);
  }

  // Process each 512-bit chunk
  for (var chunkStart = 0; chunkStart < paddedData.length; chunkStart += 64) {
    final w = List<int>.filled(64, 0);

    // Break chunk into sixteen 32-bit big-endian words
    for (var i = 0; i < 16; i++) {
      final j = chunkStart + i * 4;
      w[i] = (paddedData[j] << 24) | (paddedData[j + 1] << 16) |
             (paddedData[j + 2] << 8) | paddedData[j + 3];
    }

    // Extend the sixteen 32-bit words into sixty-four 32-bit words
    for (var i = 16; i < 64; i++) {
      final s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
      final s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & 0xffffffff;
    }

    // Initialize working variables
    var a = h0, b = h1, c = h2, d = h3;
    var e = h4, f = h5, g = h6, h = h7;

    // Compression function main loop
    for (var i = 0; i < 64; i++) {
      final s1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25);
      final ch = (e & f) ^ ((~e) & g);
      final temp1 = (h + s1 + ch + k[i] + w[i]) & 0xffffffff;
      final s0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22);
      final maj = (a & b) ^ (a & c) ^ (b & c);
      final temp2 = (s0 + maj) & 0xffffffff;

      h = g;
      g = f;
      f = e;
      e = (d + temp1) & 0xffffffff;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) & 0xffffffff;
    }

    // Add compressed chunk to current hash value
    h0 = (h0 + a) & 0xffffffff;
    h1 = (h1 + b) & 0xffffffff;
    h2 = (h2 + c) & 0xffffffff;
    h3 = (h3 + d) & 0xffffffff;
    h4 = (h4 + e) & 0xffffffff;
    h5 = (h5 + f) & 0xffffffff;
    h6 = (h6 + g) & 0xffffffff;
    h7 = (h7 + h) & 0xffffffff;
  }

  // Produce the final hash value (big-endian)
  return Uint8List.fromList([
    (h0 >> 24) & 0xff, (h0 >> 16) & 0xff, (h0 >> 8) & 0xff, h0 & 0xff,
    (h1 >> 24) & 0xff, (h1 >> 16) & 0xff, (h1 >> 8) & 0xff, h1 & 0xff,
    (h2 >> 24) & 0xff, (h2 >> 16) & 0xff, (h2 >> 8) & 0xff, h2 & 0xff,
    (h3 >> 24) & 0xff, (h3 >> 16) & 0xff, (h3 >> 8) & 0xff, h3 & 0xff,
    (h4 >> 24) & 0xff, (h4 >> 16) & 0xff, (h4 >> 8) & 0xff, h4 & 0xff,
    (h5 >> 24) & 0xff, (h5 >> 16) & 0xff, (h5 >> 8) & 0xff, h5 & 0xff,
    (h6 >> 24) & 0xff, (h6 >> 16) & 0xff, (h6 >> 8) & 0xff, h6 & 0xff,
    (h7 >> 24) & 0xff, (h7 >> 16) & 0xff, (h7 >> 8) & 0xff, h7 & 0xff,
  ]);
}

/// Right rotate for SHA256
int _rotr(int x, int n) => ((x >> n) | (x << (32 - n))) & 0xffffffff;

/// Factory function for conditional import
OidcDataSource createOidcDataSource() => OidcDataSourceWeb();
