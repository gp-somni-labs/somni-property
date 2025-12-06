import 'package:dartz/dartz.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/leases/data/datasources/lease_remote_datasource.dart';
import 'package:somni_property/features/leases/data/models/lease_model.dart';
import 'package:somni_property/features/leases/domain/entities/lease.dart';
import 'package:somni_property/features/leases/domain/repositories/lease_repository.dart';

/// Provider for lease repository
final leaseRepositoryProvider = Provider<LeaseRepository>((ref) {
  final remoteDataSource = ref.watch(leaseRemoteDataSourceProvider);
  return LeaseRepositoryImpl(remoteDataSource: remoteDataSource);
});

/// Implementation of lease repository
class LeaseRepositoryImpl implements LeaseRepository {
  final LeaseRemoteDataSource remoteDataSource;

  LeaseRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, List<Lease>>> getLeases({
    String? propertyId,
    String? tenantId,
  }) async {
    try {
      final leases = await remoteDataSource.getLeases(
        propertyId: propertyId,
        tenantId: tenantId,
      );
      return Right(leases.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Lease>> getLease(String id) async {
    try {
      final lease = await remoteDataSource.getLease(id);
      return Right(lease.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Lease>> createLease(Lease lease) async {
    try {
      final model = LeaseModel.fromEntity(lease);
      final created = await remoteDataSource.createLease(model);
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
  Future<Either<Failure, Lease>> updateLease(Lease lease) async {
    try {
      final model = LeaseModel.fromEntity(lease);
      final updated = await remoteDataSource.updateLease(model);
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
  Future<Either<Failure, void>> deleteLease(String id) async {
    try {
      await remoteDataSource.deleteLease(id);
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
  Future<Either<Failure, Lease>> renewLease(
    String id,
    DateTime newEndDate,
    double? newRent,
  ) async {
    try {
      final renewed = await remoteDataSource.renewLease(id, newEndDate, newRent);
      return Right(renewed.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Lease>> terminateLease(
    String id,
    DateTime terminationDate,
    String reason,
  ) async {
    try {
      final terminated =
          await remoteDataSource.terminateLease(id, terminationDate, reason);
      return Right(terminated.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Lease>>> getLeasesByStatus(LeaseStatus status) async {
    try {
      final leases = await remoteDataSource.getLeasesByStatus(status);
      return Right(leases.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Lease>>> getExpiringLeases(int withinDays) async {
    try {
      final leases = await remoteDataSource.getExpiringLeases(withinDays);
      return Right(leases.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Lease>>> getLeasesByUnit(String unitId) async {
    try {
      final leases = await remoteDataSource.getLeasesByUnit(unitId);
      return Right(leases.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }
}
