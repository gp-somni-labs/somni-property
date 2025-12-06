import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// Use case to get all contractors
class GetContractors {
  final ContractorRepository repository;

  GetContractors(this.repository);

  Future<Either<Failure, List<Contractor>>> call({String? propertyId}) {
    return repository.getContractors(propertyId: propertyId);
  }
}
