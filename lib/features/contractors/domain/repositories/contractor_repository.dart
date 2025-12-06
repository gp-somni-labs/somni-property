import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';

/// Repository interface for contractor operations
abstract class ContractorRepository {
  /// Get all contractors
  Future<Either<Failure, List<Contractor>>> getContractors({String? propertyId});

  /// Get contractor by ID
  Future<Either<Failure, Contractor>> getContractor(String id);

  /// Create a new contractor
  Future<Either<Failure, Contractor>> createContractor(Contractor contractor);

  /// Update existing contractor
  Future<Either<Failure, Contractor>> updateContractor(Contractor contractor);

  /// Delete contractor
  Future<Either<Failure, void>> deleteContractor(String id);

  /// Search contractors by name or company
  Future<Either<Failure, List<Contractor>>> searchContractors(String query);

  /// Get contractors by specialty
  Future<Either<Failure, List<Contractor>>> getContractorsBySpecialty(String specialty);

  /// Get contractors by status
  Future<Either<Failure, List<Contractor>>> getContractorsByStatus(ContractorStatus status);

  /// Get available contractors
  Future<Either<Failure, List<Contractor>>> getAvailableContractors();

  /// Assign contractor to work order
  Future<Either<Failure, void>> assignToWorkOrder({
    required String contractorId,
    required String workOrderId,
    required double estimatedHours,
    DateTime? startDate,
    String? notes,
  });

  /// Track labor time for contractor
  Future<Either<Failure, LaborTime>> trackLaborTime({
    required String contractorId,
    required String workOrderId,
    required DateTime date,
    required double hoursWorked,
    required double overtimeHours,
    String? description,
  });

  /// Get labor time entries for contractor
  Future<Either<Failure, List<LaborTime>>> getLaborTimeEntries({
    required String contractorId,
    String? workOrderId,
    DateTime? startDate,
    DateTime? endDate,
  });

  /// Rate contractor for a work order
  Future<Either<Failure, ContractorRating>> rateContractor({
    required String contractorId,
    required String workOrderId,
    required int rating,
    required int qualityRating,
    required int communicationRating,
    required int timelinessRating,
    String? review,
  });

  /// Get ratings for contractor
  Future<Either<Failure, List<ContractorRating>>> getContractorRatings(String contractorId);

  /// Get contractor performance metrics
  Future<Either<Failure, ContractorPerformance>> getContractorPerformance(String contractorId);

  /// Get contractor work orders
  Future<Either<Failure, List<dynamic>>> getContractorWorkOrders({
    required String contractorId,
    String? status,
  });

  /// Update contractor availability
  Future<Either<Failure, Contractor>> updateAvailability({
    required String contractorId,
    required Availability availability,
  });
}
