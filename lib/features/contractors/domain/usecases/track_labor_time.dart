import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// Use case to track labor time for a contractor
class TrackLaborTime {
  final ContractorRepository repository;

  TrackLaborTime(this.repository);

  Future<Either<Failure, LaborTime>> call({
    required String contractorId,
    required String workOrderId,
    required DateTime date,
    required double hoursWorked,
    required double overtimeHours,
    String? description,
  }) {
    return repository.trackLaborTime(
      contractorId: contractorId,
      workOrderId: workOrderId,
      date: date,
      hoursWorked: hoursWorked,
      overtimeHours: overtimeHours,
      description: description,
    );
  }
}
