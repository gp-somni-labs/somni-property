import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// Use case to assign contractor to a work order
class AssignToWorkOrder {
  final ContractorRepository repository;

  AssignToWorkOrder(this.repository);

  Future<Either<Failure, void>> call({
    required String contractorId,
    required String workOrderId,
    required double estimatedHours,
    DateTime? startDate,
    String? notes,
  }) {
    return repository.assignToWorkOrder(
      contractorId: contractorId,
      workOrderId: workOrderId,
      estimatedHours: estimatedHours,
      startDate: startDate,
      notes: notes,
    );
  }
}
