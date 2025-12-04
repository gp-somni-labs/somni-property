import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:somni_property/core/constants/app_constants.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/network/network_info.dart';

/// Provider for the API client
final apiClientProvider = Provider<ApiClient>((ref) {
  final networkInfo = ref.watch(networkInfoProvider);
  return ApiClient(networkInfo: networkInfo);
});

/// Centralized API client with JWT handling
class ApiClient {
  late final Dio _dio;
  final NetworkInfo networkInfo;
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();

  ApiClient({required this.networkInfo}) {
    _dio = Dio(
      BaseOptions(
        // Set default base URL - will be updated dynamically if VPN detected
        baseUrl: '${AppConstants.localBaseUrl}${AppConstants.apiVersion}',
        connectTimeout: AppConstants.connectionTimeout,
        receiveTimeout: AppConstants.receiveTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    _dio.interceptors.add(_BaseUrlInterceptor(this));
    _dio.interceptors.add(_AuthInterceptor(this));
    _dio.interceptors.add(_LoggingInterceptor());
  }

  Dio get dio => _dio;

  /// Initialize base URL based on network status
  Future<void> initializeBaseUrl() async {
    final baseUrl = await networkInfo.currentBaseUrl;
    _dio.options.baseUrl = '$baseUrl${AppConstants.apiVersion}';
  }

  /// Get stored access token
  Future<String?> getAccessToken() async {
    return await _secureStorage.read(key: AppConstants.accessTokenKey);
  }

  /// Get stored refresh token
  Future<String?> getRefreshToken() async {
    return await _secureStorage.read(key: AppConstants.refreshTokenKey);
  }

  /// Store tokens after login
  Future<void> storeTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _secureStorage.write(
      key: AppConstants.accessTokenKey,
      value: accessToken,
    );
    await _secureStorage.write(
      key: AppConstants.refreshTokenKey,
      value: refreshToken,
    );
  }

  /// Clear tokens on logout
  Future<void> clearTokens() async {
    await _secureStorage.delete(key: AppConstants.accessTokenKey);
    await _secureStorage.delete(key: AppConstants.refreshTokenKey);
    await _secureStorage.delete(key: AppConstants.userIdKey);
    await _secureStorage.delete(key: AppConstants.userRoleKey);
  }

  /// Store user info
  Future<void> storeUserInfo({
    required String userId,
    required String role,
  }) async {
    await _secureStorage.write(key: AppConstants.userIdKey, value: userId);
    await _secureStorage.write(key: AppConstants.userRoleKey, value: role);
  }

  /// Get user ID
  Future<String?> getUserId() async {
    return await _secureStorage.read(key: AppConstants.userIdKey);
  }

  /// Refresh the access token
  Future<String> refreshAccessToken() async {
    final refreshToken = await getRefreshToken();
    if (refreshToken == null) {
      throw const TokenExpiredException();
    }

    try {
      final response = await _dio.post(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
        options: Options(
          headers: {'Authorization': null}, // Don't send expired token
        ),
      );

      final newAccessToken = response.data['access_token'] as String;
      final newRefreshToken = response.data['refresh_token'] as String;

      await storeTokens(
        accessToken: newAccessToken,
        refreshToken: newRefreshToken,
      );

      return newAccessToken;
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        await clearTokens();
        throw const TokenExpiredException();
      }
      rethrow;
    }
  }
}

/// Interceptor for dynamically updating base URL based on VPN status
class _BaseUrlInterceptor extends Interceptor {
  final ApiClient apiClient;
  bool _initialized = false;

  _BaseUrlInterceptor(this.apiClient);

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Update base URL on first request or when it might have changed
    if (!_initialized) {
      final baseUrl = await apiClient.networkInfo.currentBaseUrl;
      apiClient._dio.options.baseUrl = '$baseUrl${AppConstants.apiVersion}';
      _initialized = true;
      debugPrint('Base URL initialized to: ${apiClient._dio.options.baseUrl}');
    }
    return handler.next(options);
  }
}

/// Interceptor for adding auth headers and handling token refresh
class _AuthInterceptor extends Interceptor {
  final ApiClient apiClient;

  _AuthInterceptor(this.apiClient);

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Skip auth for login/register endpoints
    if (options.path.contains('/auth/login') ||
        options.path.contains('/auth/register')) {
      return handler.next(options);
    }

    final token = await apiClient.getAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }

    return handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401) {
      // Try to refresh token
      try {
        final newToken = await apiClient.refreshAccessToken();

        // Retry original request with new token
        final options = err.requestOptions;
        options.headers['Authorization'] = 'Bearer $newToken';

        final response = await apiClient.dio.fetch(options);
        return handler.resolve(response);
      } on TokenExpiredException {
        // Token refresh failed, need to re-login
        return handler.reject(err);
      }
    }

    return handler.next(err);
  }
}

/// Logging interceptor for debugging
class _LoggingInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    debugPrint('API Request: ${options.method} ${options.uri}');
    return handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    debugPrint(
        'API Response: ${response.statusCode} ${response.requestOptions.uri}');
    return handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    debugPrint('API Error: ${err.response?.statusCode} ${err.message}');
    return handler.next(err);
  }
}

/// Extension to convert DioException to app exceptions
extension DioExceptionExtension on DioException {
  AppException toAppException() {
    switch (type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const NetworkException(message: 'Connection timed out');
      case DioExceptionType.connectionError:
        return const NetworkException(message: 'Unable to connect to server');
      case DioExceptionType.badResponse:
        final statusCode = response?.statusCode;
        final message = response?.data?['message'] ?? 'Server error';
        if (statusCode == 401) {
          return AuthException(message: message, statusCode: statusCode);
        }
        return ServerException(message: message, statusCode: statusCode);
      default:
        return ServerException(
          message: message ?? 'Unknown error occurred',
        );
    }
  }
}
