import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// Use case to get a single contractor by ID
class GetContractor {
  final ContractorRepository repository;

  GetContractor(this.repository);

  Future<Either<Failure, Contractor>> call(String id) {
    return repository.getContractor(id);
  }
}
