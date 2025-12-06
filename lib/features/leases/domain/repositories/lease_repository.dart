import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/leases/domain/entities/lease.dart';

/// Abstract repository for lease operations
abstract class LeaseRepository {
  /// Get all leases, optionally filtered by property or tenant
  Future<Either<Failure, List<Lease>>> getLeases({
    String? propertyId,
    String? tenantId,
  });

  /// Get a single lease by ID
  Future<Either<Failure, Lease>> getLease(String id);

  /// Create a new lease
  Future<Either<Failure, Lease>> createLease(Lease lease);

  /// Update an existing lease
  Future<Either<Failure, Lease>> updateLease(Lease lease);

  /// Delete a lease
  Future<Either<Failure, void>> deleteLease(String id);

  /// Renew a lease
  Future<Either<Failure, Lease>> renewLease(
    String id,
    DateTime newEndDate,
    double? newRent,
  );

  /// Terminate a lease
  Future<Either<Failure, Lease>> terminateLease(
    String id,
    DateTime terminationDate,
    String reason,
  );

  /// Get leases by status
  Future<Either<Failure, List<Lease>>> getLeasesByStatus(LeaseStatus status);

  /// Get expiring leases (within specified days)
  Future<Either<Failure, List<Lease>>> getExpiringLeases(int withinDays);

  /// Get leases by unit
  Future<Either<Failure, List<Lease>>> getLeasesByUnit(String unitId);
}
