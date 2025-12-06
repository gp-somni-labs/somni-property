import 'package:dartz/dartz.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/tenants/data/datasources/tenant_remote_datasource.dart';
import 'package:somni_property/features/tenants/data/models/tenant_model.dart';
import 'package:somni_property/features/tenants/domain/entities/tenant.dart';
import 'package:somni_property/features/tenants/domain/repositories/tenant_repository.dart';

/// Provider for tenant repository
final tenantRepositoryProvider = Provider<TenantRepository>((ref) {
  final remoteDataSource = ref.watch(tenantRemoteDataSourceProvider);
  return TenantRepositoryImpl(remoteDataSource: remoteDataSource);
});

/// Implementation of tenant repository
class TenantRepositoryImpl implements TenantRepository {
  final TenantRemoteDataSource remoteDataSource;

  TenantRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, List<Tenant>>> getTenants({String? propertyId}) async {
    try {
      final tenants = await remoteDataSource.getTenants(propertyId: propertyId);
      return Right(tenants.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Tenant>> getTenant(String id) async {
    try {
      final tenant = await remoteDataSource.getTenant(id);
      return Right(tenant.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Tenant>> createTenant(Tenant tenant) async {
    try {
      final model = TenantModel.fromEntity(tenant);
      final created = await remoteDataSource.createTenant(model);
      return Right(created.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Tenant>> updateTenant(Tenant tenant) async {
    try {
      final model = TenantModel.fromEntity(tenant);
      final updated = await remoteDataSource.updateTenant(model);
      return Right(updated.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> deleteTenant(String id) async {
    try {
      await remoteDataSource.deleteTenant(id);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Tenant>>> searchTenants(String query) async {
    try {
      final tenants = await remoteDataSource.searchTenants(query);
      return Right(tenants.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Tenant>>> getTenantsByUnit(String unitId) async {
    try {
      final tenants = await remoteDataSource.getTenantsByUnit(unitId);
      return Right(tenants.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Tenant>>> getTenantsByStatus(
      TenantStatus status) async {
    try {
      final tenants = await remoteDataSource.getTenantsByStatus(status);
      return Right(tenants.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }
}
