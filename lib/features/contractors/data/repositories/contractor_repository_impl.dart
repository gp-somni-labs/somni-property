import 'package:dartz/dartz.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/contractors/data/datasources/contractor_remote_datasource.dart';
import 'package:somni_property/features/contractors/data/models/contractor_model.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// Provider for contractor repository
final contractorRepositoryProvider = Provider<ContractorRepository>((ref) {
  final remoteDataSource = ref.watch(contractorRemoteDataSourceProvider);
  return ContractorRepositoryImpl(remoteDataSource: remoteDataSource);
});

/// Implementation of contractor repository
class ContractorRepositoryImpl implements ContractorRepository {
  final ContractorRemoteDataSource remoteDataSource;

  ContractorRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, List<Contractor>>> getContractors(
      {String? propertyId}) async {
    try {
      final contractors =
          await remoteDataSource.getContractors(propertyId: propertyId);
      return Right(contractors.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Contractor>> getContractor(String id) async {
    try {
      final contractor = await remoteDataSource.getContractor(id);
      return Right(contractor.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Contractor>> createContractor(
      Contractor contractor) async {
    try {
      final model = ContractorModel.fromEntity(contractor);
      final created = await remoteDataSource.createContractor(model);
      return Right(created.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Contractor>> updateContractor(
      Contractor contractor) async {
    try {
      final model = ContractorModel.fromEntity(contractor);
      final updated = await remoteDataSource.updateContractor(model);
      return Right(updated.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> deleteContractor(String id) async {
    try {
      await remoteDataSource.deleteContractor(id);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Contractor>>> searchContractors(
      String query) async {
    try {
      final contractors = await remoteDataSource.searchContractors(query);
      return Right(contractors.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Contractor>>> getContractorsBySpecialty(
      String specialty) async {
    try {
      final contractors =
          await remoteDataSource.getContractorsBySpecialty(specialty);
      return Right(contractors.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Contractor>>> getContractorsByStatus(
      ContractorStatus status) async {
    try {
      final contractors =
          await remoteDataSource.getContractorsByStatus(status);
      return Right(contractors.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Contractor>>> getAvailableContractors() async {
    try {
      final contractors = await remoteDataSource.getAvailableContractors();
      return Right(contractors.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> assignToWorkOrder({
    required String contractorId,
    required String workOrderId,
    required double estimatedHours,
    DateTime? startDate,
    String? notes,
  }) async {
    try {
      await remoteDataSource.assignToWorkOrder(
        contractorId: contractorId,
        workOrderId: workOrderId,
        estimatedHours: estimatedHours,
        startDate: startDate,
        notes: notes,
      );
      return const Right(null);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, LaborTime>> trackLaborTime({
    required String contractorId,
    required String workOrderId,
    required DateTime date,
    required double hoursWorked,
    required double overtimeHours,
    String? description,
  }) async {
    try {
      final laborTime = await remoteDataSource.trackLaborTime(
        contractorId: contractorId,
        workOrderId: workOrderId,
        date: date,
        hoursWorked: hoursWorked,
        overtimeHours: overtimeHours,
        description: description,
      );
      return Right(laborTime.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<LaborTime>>> getLaborTimeEntries({
    required String contractorId,
    String? workOrderId,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      final entries = await remoteDataSource.getLaborTimeEntries(
        contractorId: contractorId,
        workOrderId: workOrderId,
        startDate: startDate,
        endDate: endDate,
      );
      return Right(entries.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, ContractorRating>> rateContractor({
    required String contractorId,
    required String workOrderId,
    required int rating,
    required int qualityRating,
    required int communicationRating,
    required int timelinessRating,
    String? review,
  }) async {
    try {
      final ratingResult = await remoteDataSource.rateContractor(
        contractorId: contractorId,
        workOrderId: workOrderId,
        rating: rating,
        qualityRating: qualityRating,
        communicationRating: communicationRating,
        timelinessRating: timelinessRating,
        review: review,
      );
      return Right(ratingResult.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<ContractorRating>>> getContractorRatings(
      String contractorId) async {
    try {
      final ratings =
          await remoteDataSource.getContractorRatings(contractorId);
      return Right(ratings.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, ContractorPerformance>> getContractorPerformance(
      String contractorId) async {
    try {
      final performance =
          await remoteDataSource.getContractorPerformance(contractorId);
      return Right(performance.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<dynamic>>> getContractorWorkOrders({
    required String contractorId,
    String? status,
  }) async {
    try {
      final workOrders = await remoteDataSource.getContractorWorkOrders(
        contractorId: contractorId,
        status: status,
      );
      return Right(workOrders);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Contractor>> updateAvailability({
    required String contractorId,
    required Availability availability,
  }) async {
    try {
      final contractor = await remoteDataSource.updateAvailability(
        contractorId: contractorId,
        availability: availability,
      );
      return Right(contractor.toEntity());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }
}
