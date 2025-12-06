import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/contractors/data/models/contractor_model.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';

/// Provider for contractor remote data source
final contractorRemoteDataSourceProvider =
    Provider<ContractorRemoteDataSource>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ContractorRemoteDataSourceImpl(apiClient: apiClient);
});

/// Abstract interface for contractor remote operations
abstract class ContractorRemoteDataSource {
  // Basic CRUD
  Future<List<ContractorModel>> getContractors({String? propertyId});
  Future<ContractorModel> getContractor(String id);
  Future<ContractorModel> createContractor(ContractorModel contractor);
  Future<ContractorModel> updateContractor(ContractorModel contractor);
  Future<void> deleteContractor(String id);

  // Search and filter
  Future<List<ContractorModel>> searchContractors(String query);
  Future<List<ContractorModel>> getContractorsBySpecialty(String specialty);
  Future<List<ContractorModel>> getContractorsByStatus(ContractorStatus status);
  Future<List<ContractorModel>> getAvailableContractors();

  // Work order operations
  Future<void> assignToWorkOrder({
    required String contractorId,
    required String workOrderId,
    required double estimatedHours,
    DateTime? startDate,
    String? notes,
  });
  Future<List<dynamic>> getContractorWorkOrders({
    required String contractorId,
    String? status,
  });

  // Labor time tracking
  Future<LaborTimeModel> trackLaborTime({
    required String contractorId,
    required String workOrderId,
    required DateTime date,
    required double hoursWorked,
    required double overtimeHours,
    String? description,
  });
  Future<List<LaborTimeModel>> getLaborTimeEntries({
    required String contractorId,
    String? workOrderId,
    DateTime? startDate,
    DateTime? endDate,
  });

  // Rating and performance
  Future<ContractorRatingModel> rateContractor({
    required String contractorId,
    required String workOrderId,
    required int rating,
    required int qualityRating,
    required int communicationRating,
    required int timelinessRating,
    String? review,
  });
  Future<List<ContractorRatingModel>> getContractorRatings(String contractorId);
  Future<ContractorPerformanceModel> getContractorPerformance(
      String contractorId);

  // Availability
  Future<ContractorModel> updateAvailability({
    required String contractorId,
    required Availability availability,
  });

  // Statistics
  Future<ContractorStatsModel> getContractorStats();
}

/// Implementation of contractor remote data source
class ContractorRemoteDataSourceImpl implements ContractorRemoteDataSource {
  final ApiClient apiClient;

  ContractorRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<List<ContractorModel>> getContractors({String? propertyId}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (propertyId != null) {
        queryParams['property_id'] = propertyId;
      }

      final response = await apiClient.dio.get(
        '/contractors',
        queryParameters: queryParams.isNotEmpty ? queryParams : null,
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) =>
              ContractorModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<ContractorModel> getContractor(String id) async {
    try {
      final response = await apiClient.dio.get('/contractors/$id');
      return ContractorModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<ContractorModel> createContractor(
      ContractorModel contractor) async {
    try {
      final response = await apiClient.dio.post(
        '/contractors',
        data: contractor.toCreateJson(),
      );
      return ContractorModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<ContractorModel> updateContractor(
      ContractorModel contractor) async {
    try {
      final response = await apiClient.dio.put(
        '/contractors/${contractor.id}',
        data: contractor.toJson(),
      );
      return ContractorModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<void> deleteContractor(String id) async {
    try {
      await apiClient.dio.delete('/contractors/$id');
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<ContractorModel>> searchContractors(String query) async {
    try {
      final response = await apiClient.dio.get(
        '/contractors/search',
        queryParameters: {'q': query},
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) =>
              ContractorModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<ContractorModel>> getContractorsBySpecialty(
      String specialty) async {
    try {
      final response = await apiClient.dio.get(
        '/contractors',
        queryParameters: {'specialty': specialty},
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) =>
              ContractorModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<ContractorModel>> getContractorsByStatus(
      ContractorStatus status) async {
    try {
      final response = await apiClient.dio.get(
        '/contractors',
        queryParameters: {'status': status.name},
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) =>
              ContractorModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<ContractorModel>> getAvailableContractors() async {
    try {
      final response = await apiClient.dio.get('/contractors/available');

      final data = response.data as List<dynamic>;
      return data
          .map((json) =>
              ContractorModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<void> assignToWorkOrder({
    required String contractorId,
    required String workOrderId,
    required double estimatedHours,
    DateTime? startDate,
    String? notes,
  }) async {
    try {
      await apiClient.dio.post(
        '/contractors/$contractorId/assign',
        data: {
          'work_order_id': workOrderId,
          'estimated_hours': estimatedHours,
          if (startDate != null) 'start_date': startDate.toIso8601String(),
          if (notes != null) 'notes': notes,
        },
      );
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<dynamic>> getContractorWorkOrders({
    required String contractorId,
    String? status,
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (status != null) {
        queryParams['status'] = status;
      }

      final response = await apiClient.dio.get(
        '/contractors/$contractorId/work-orders',
        queryParameters: queryParams.isNotEmpty ? queryParams : null,
      );

      return response.data as List<dynamic>;
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<LaborTimeModel> trackLaborTime({
    required String contractorId,
    required String workOrderId,
    required DateTime date,
    required double hoursWorked,
    required double overtimeHours,
    String? description,
  }) async {
    try {
      final response = await apiClient.dio.post(
        '/contractors/$contractorId/labor-time',
        data: {
          'work_order_id': workOrderId,
          'date': date.toIso8601String(),
          'hours_worked': hoursWorked,
          'overtime_hours': overtimeHours,
          if (description != null) 'description': description,
        },
      );

      return LaborTimeModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<LaborTimeModel>> getLaborTimeEntries({
    required String contractorId,
    String? workOrderId,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (workOrderId != null) {
        queryParams['work_order_id'] = workOrderId;
      }
      if (startDate != null) {
        queryParams['start_date'] = startDate.toIso8601String();
      }
      if (endDate != null) {
        queryParams['end_date'] = endDate.toIso8601String();
      }

      final response = await apiClient.dio.get(
        '/contractors/$contractorId/labor-time',
        queryParameters: queryParams.isNotEmpty ? queryParams : null,
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) =>
              LaborTimeModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<ContractorRatingModel> rateContractor({
    required String contractorId,
    required String workOrderId,
    required int rating,
    required int qualityRating,
    required int communicationRating,
    required int timelinessRating,
    String? review,
  }) async {
    try {
      final response = await apiClient.dio.post(
        '/contractors/$contractorId/ratings',
        data: {
          'work_order_id': workOrderId,
          'rating': rating,
          'quality_rating': qualityRating,
          'communication_rating': communicationRating,
          'timeliness_rating': timelinessRating,
          if (review != null) 'review': review,
        },
      );

      return ContractorRatingModel.fromJson(
          response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<ContractorRatingModel>> getContractorRatings(
      String contractorId) async {
    try {
      final response =
          await apiClient.dio.get('/contractors/$contractorId/ratings');

      final data = response.data as List<dynamic>;
      return data
          .map((json) =>
              ContractorRatingModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<ContractorPerformanceModel> getContractorPerformance(
      String contractorId) async {
    try {
      final response =
          await apiClient.dio.get('/contractors/$contractorId/performance');

      return ContractorPerformanceModel.fromJson(
          response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<ContractorModel> updateAvailability({
    required String contractorId,
    required Availability availability,
  }) async {
    try {
      final response = await apiClient.dio.put(
        '/contractors/$contractorId/availability',
        data: {'availability': availability.toJson()},
      );

      return ContractorModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<ContractorStatsModel> getContractorStats() async {
    try {
      final response = await apiClient.dio.get('/contractors/stats');
      return ContractorStatsModel.fromJson(
          response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }
}
