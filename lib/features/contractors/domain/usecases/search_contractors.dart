import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// Use case to search contractors
class SearchContractors {
  final ContractorRepository repository;

  SearchContractors(this.repository);

  Future<Either<Failure, List<Contractor>>> call(String query) {
    return repository.searchContractors(query);
  }
}
