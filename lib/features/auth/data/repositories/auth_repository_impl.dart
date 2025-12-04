import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/core/network/network_info.dart';
import 'package:somni_property/features/auth/data/datasources/auth_local_datasource.dart';
import 'package:somni_property/features/auth/data/datasources/auth_remote_datasource.dart';
import 'package:somni_property/features/auth/domain/entities/user.dart';
import 'package:somni_property/features/auth/domain/repositories/auth_repository.dart';

/// Implementation of AuthRepository
class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource remoteDataSource;
  final AuthLocalDataSource localDataSource;
  final NetworkInfo networkInfo;

  AuthRepositoryImpl({
    required this.remoteDataSource,
    required this.localDataSource,
    required this.networkInfo,
  });

  @override
  Future<Either<Failure, User>> login(LoginCredentials credentials) async {
    if (!await networkInfo.isConnected) {
      return const Left(NetworkFailure());
    }

    // Check VPN status for security
    final isVpnConnected = await networkInfo.isVpnConnected;
    if (!isVpnConnected) {
      // Allow login but warn - could also require VPN
      // return const Left(VpnFailure());
    }

    try {
      final response = await remoteDataSource.login(credentials);

      // Cache user and tokens locally
      await localDataSource.cacheUser(response.user);
      await localDataSource.cacheTokens(response.tokens);

      return Right(response.user.toEntity());
    } on InvalidCredentialsException {
      return const Left(InvalidCredentialsFailure());
    } on AuthException catch (e) {
      return Left(AuthFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException {
      return const Left(NetworkFailure());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } catch (e) {
      return Left(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> logout() async {
    try {
      // Try to logout on server if connected
      if (await networkInfo.isConnected) {
        try {
          await remoteDataSource.logout();
        } catch (_) {
          // Server logout failed, but continue with local cleanup
        }
      }

      // Always clear local cache
      await localDataSource.clearCache();
      return const Right(null);
    } on CacheException catch (e) {
      return Left(CacheFailure(message: e.message));
    } catch (e) {
      return Left(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, User>> getCurrentUser() async {
    try {
      // Try to get from server if connected
      if (await networkInfo.isConnected) {
        try {
          final user = await remoteDataSource.getCurrentUser();
          await localDataSource.cacheUser(user);
          return Right(user.toEntity());
        } catch (_) {
          // Fall through to cached data
        }
      }

      // Get from local cache
      final cachedUser = await localDataSource.getCachedUser();
      if (cachedUser != null) {
        return Right(cachedUser.toEntity());
      }

      return const Left(AuthFailure(
        message: 'No user data available',
        statusCode: 401,
      ));
    } on AuthException catch (e) {
      return Left(AuthFailure(message: e.message, statusCode: e.statusCode));
    } catch (e) {
      return Left(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<bool> isAuthenticated() async {
    return await localDataSource.hasValidSession();
  }

  @override
  Future<Either<Failure, AuthTokens>> refreshToken() async {
    if (!await networkInfo.isConnected) {
      return const Left(NetworkFailure());
    }

    try {
      final cachedTokens = await localDataSource.getCachedTokens();
      if (cachedTokens == null) {
        return const Left(TokenExpiredFailure());
      }

      final newTokens = await remoteDataSource.refreshToken(
        cachedTokens.refreshToken,
      );
      await localDataSource.cacheTokens(newTokens);

      return Right(newTokens);
    } on TokenExpiredException {
      await localDataSource.clearCache();
      return const Left(TokenExpiredFailure());
    } on AuthException catch (e) {
      return Left(AuthFailure(message: e.message, statusCode: e.statusCode));
    } catch (e) {
      return Left(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, bool>> verifyTwoFactor(String code) async {
    if (!await networkInfo.isConnected) {
      return const Left(NetworkFailure());
    }

    try {
      final verified = await remoteDataSource.verifyTwoFactor(code);
      return Right(verified);
    } on AuthException catch (e) {
      return Left(AuthFailure(message: e.message, statusCode: e.statusCode));
    } catch (e) {
      return Left(UnknownFailure(message: e.toString()));
    }
  }
}
