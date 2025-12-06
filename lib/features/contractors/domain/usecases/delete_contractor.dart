import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// Use case to delete a contractor
class DeleteContractor {
  final ContractorRepository repository;

  DeleteContractor(this.repository);

  Future<Either<Failure, void>> call(String id) {
    return repository.deleteContractor(id);
  }
}
