import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// Use case to get contractor performance metrics
class GetContractorPerformance {
  final ContractorRepository repository;

  GetContractorPerformance(this.repository);

  Future<Either<Failure, ContractorPerformance>> call(String contractorId) {
    return repository.getContractorPerformance(contractorId);
  }
}
