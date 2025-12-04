import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:somni_property/core/constants/app_constants.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/features/auth/data/models/user_model.dart';

/// Local data source for caching auth data
abstract class AuthLocalDataSource {
  Future<void> cacheUser(UserModel user);
  Future<UserModel?> getCachedUser();
  Future<void> cacheTokens(AuthTokensModel tokens);
  Future<AuthTokensModel?> getCachedTokens();
  Future<void> clearCache();
  Future<bool> hasValidSession();
}

/// Implementation of auth local data source using secure storage
class AuthLocalDataSourceImpl implements AuthLocalDataSource {
  final FlutterSecureStorage secureStorage;

  static const String _userKey = 'cached_user';
  static const String _tokensKey = 'cached_tokens';

  AuthLocalDataSourceImpl({required this.secureStorage});

  @override
  Future<void> cacheUser(UserModel user) async {
    try {
      await secureStorage.write(
        key: _userKey,
        value: jsonEncode(user.toJson()),
      );
    } catch (e) {
      throw CacheException(message: 'Failed to cache user: $e');
    }
  }

  @override
  Future<UserModel?> getCachedUser() async {
    try {
      final jsonString = await secureStorage.read(key: _userKey);
      if (jsonString == null) return null;

      final json = jsonDecode(jsonString) as Map<String, dynamic>;
      return UserModel.fromJson(json);
    } catch (e) {
      return null;
    }
  }

  @override
  Future<void> cacheTokens(AuthTokensModel tokens) async {
    try {
      await secureStorage.write(
        key: AppConstants.accessTokenKey,
        value: tokens.accessToken,
      );
      await secureStorage.write(
        key: AppConstants.refreshTokenKey,
        value: tokens.refreshToken,
      );
      await secureStorage.write(
        key: _tokensKey,
        value: jsonEncode(tokens.toJson()),
      );
    } catch (e) {
      throw CacheException(message: 'Failed to cache tokens: $e');
    }
  }

  @override
  Future<AuthTokensModel?> getCachedTokens() async {
    try {
      final jsonString = await secureStorage.read(key: _tokensKey);
      if (jsonString == null) return null;

      final json = jsonDecode(jsonString) as Map<String, dynamic>;
      return AuthTokensModel.fromJson(json);
    } catch (e) {
      return null;
    }
  }

  @override
  Future<void> clearCache() async {
    try {
      await secureStorage.delete(key: _userKey);
      await secureStorage.delete(key: _tokensKey);
      await secureStorage.delete(key: AppConstants.accessTokenKey);
      await secureStorage.delete(key: AppConstants.refreshTokenKey);
      await secureStorage.delete(key: AppConstants.userIdKey);
      await secureStorage.delete(key: AppConstants.userRoleKey);
    } catch (e) {
      throw CacheException(message: 'Failed to clear cache: $e');
    }
  }

  @override
  Future<bool> hasValidSession() async {
    try {
      final tokens = await getCachedTokens();
      if (tokens == null) return false;

      // Check if access token exists and is not expired
      return !tokens.isExpired;
    } catch (e) {
      return false;
    }
  }
}
