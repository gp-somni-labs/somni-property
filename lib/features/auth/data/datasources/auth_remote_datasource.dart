import 'package:dio/dio.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/auth/data/models/user_model.dart';
import 'package:somni_property/features/auth/domain/entities/user.dart';

/// Remote data source for authentication
abstract class AuthRemoteDataSource {
  Future<LoginResponse> login(LoginCredentials credentials);
  Future<void> logout();
  Future<UserModel> getCurrentUser();
  Future<AuthTokensModel> refreshToken(String refreshToken);
  Future<bool> verifyTwoFactor(String code);
}

/// Implementation of auth remote data source
class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final ApiClient apiClient;

  AuthRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<LoginResponse> login(LoginCredentials credentials) async {
    try {
      final response = await apiClient.dio.post(
        '/auth/login',
        data: {
          'username': credentials.username,
          'password': credentials.password,
          if (credentials.totpCode != null) 'totp_code': credentials.totpCode,
        },
      );

      return LoginResponse.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw const InvalidCredentialsException();
      }
      if (e.response?.statusCode == 403) {
        throw const AuthException(
          message: 'Two-factor authentication required',
          statusCode: 403,
        );
      }
      throw e.toAppException();
    }
  }

  @override
  Future<void> logout() async {
    try {
      await apiClient.dio.post('/auth/logout');
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<UserModel> getCurrentUser() async {
    try {
      final response = await apiClient.dio.get('/auth/me');
      return UserModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<AuthTokensModel> refreshToken(String refreshToken) async {
    try {
      final response = await apiClient.dio.post(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      return AuthTokensModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw const TokenExpiredException();
      }
      throw e.toAppException();
    }
  }

  @override
  Future<bool> verifyTwoFactor(String code) async {
    try {
      final response = await apiClient.dio.post(
        '/auth/2fa/verify',
        data: {'code': code},
      );
      return response.data['verified'] as bool? ?? false;
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }
}
