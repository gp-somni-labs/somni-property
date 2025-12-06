import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// Use case to create a new contractor
class CreateContractor {
  final ContractorRepository repository;

  CreateContractor(this.repository);

  Future<Either<Failure, Contractor>> call(Contractor contractor) {
    return repository.createContractor(contractor);
  }
}
