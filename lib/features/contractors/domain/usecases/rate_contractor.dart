import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// Use case to rate a contractor
class RateContractor {
  final ContractorRepository repository;

  RateContractor(this.repository);

  Future<Either<Failure, ContractorRating>> call({
    required String contractorId,
    required String workOrderId,
    required int rating,
    required int qualityRating,
    required int communicationRating,
    required int timelinessRating,
    String? review,
  }) {
    return repository.rateContractor(
      contractorId: contractorId,
      workOrderId: workOrderId,
      rating: rating,
      qualityRating: qualityRating,
      communicationRating: communicationRating,
      timelinessRating: timelinessRating,
      review: review,
    );
  }
}
