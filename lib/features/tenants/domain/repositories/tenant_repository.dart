import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/tenants/domain/entities/tenant.dart';

/// Abstract repository for tenant operations
abstract class TenantRepository {
  /// Get all tenants, optionally filtered by property
  Future<Either<Failure, List<Tenant>>> getTenants({String? propertyId});

  /// Get a single tenant by ID
  Future<Either<Failure, Tenant>> getTenant(String id);

  /// Create a new tenant
  Future<Either<Failure, Tenant>> createTenant(Tenant tenant);

  /// Update an existing tenant
  Future<Either<Failure, Tenant>> updateTenant(Tenant tenant);

  /// Delete a tenant
  Future<Either<Failure, void>> deleteTenant(String id);

  /// Search tenants by name or email
  Future<Either<Failure, List<Tenant>>> searchTenants(String query);

  /// Get tenants by unit
  Future<Either<Failure, List<Tenant>>> getTenantsByUnit(String unitId);

  /// Get tenants by status
  Future<Either<Failure, List<Tenant>>> getTenantsByStatus(TenantStatus status);
}
