import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/leases/data/models/lease_model.dart';
import 'package:somni_property/features/leases/domain/entities/lease.dart';

/// Provider for lease remote data source
final leaseRemoteDataSourceProvider = Provider<LeaseRemoteDataSource>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return LeaseRemoteDataSourceImpl(apiClient: apiClient);
});

/// Abstract interface for lease remote operations
abstract class LeaseRemoteDataSource {
  Future<List<LeaseModel>> getLeases({String? propertyId, String? tenantId});
  Future<LeaseModel> getLease(String id);
  Future<LeaseModel> createLease(LeaseModel lease);
  Future<LeaseModel> updateLease(LeaseModel lease);
  Future<void> deleteLease(String id);
  Future<LeaseModel> renewLease(String id, DateTime newEndDate, double? newRent);
  Future<LeaseModel> terminateLease(String id, DateTime terminationDate, String reason);
  Future<List<LeaseModel>> getLeasesByStatus(LeaseStatus status);
  Future<List<LeaseModel>> getExpiringLeases(int withinDays);
  Future<List<LeaseModel>> getLeasesByUnit(String unitId);
}

/// Implementation of lease remote data source
class LeaseRemoteDataSourceImpl implements LeaseRemoteDataSource {
  final ApiClient apiClient;

  LeaseRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<List<LeaseModel>> getLeases({String? propertyId, String? tenantId}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (propertyId != null) queryParams['property_id'] = propertyId;
      if (tenantId != null) queryParams['tenant_id'] = tenantId;

      final response = await apiClient.dio.get(
        '/leases',
        queryParameters: queryParams.isNotEmpty ? queryParams : null,
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) => LeaseModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<LeaseModel> getLease(String id) async {
    try {
      final response = await apiClient.dio.get('/leases/$id');
      return LeaseModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<LeaseModel> createLease(LeaseModel lease) async {
    try {
      final response = await apiClient.dio.post(
        '/leases',
        data: lease.toCreateJson(),
      );
      return LeaseModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<LeaseModel> updateLease(LeaseModel lease) async {
    try {
      final response = await apiClient.dio.put(
        '/leases/${lease.id}',
        data: lease.toJson(),
      );
      return LeaseModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<void> deleteLease(String id) async {
    try {
      await apiClient.dio.delete('/leases/$id');
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<LeaseModel> renewLease(String id, DateTime newEndDate, double? newRent) async {
    try {
      final response = await apiClient.dio.post(
        '/leases/$id/renew',
        data: {
          'new_end_date': newEndDate.toIso8601String(),
          if (newRent != null) 'new_rent': newRent,
        },
      );
      return LeaseModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<LeaseModel> terminateLease(String id, DateTime terminationDate, String reason) async {
    try {
      final response = await apiClient.dio.post(
        '/leases/$id/terminate',
        data: {
          'termination_date': terminationDate.toIso8601String(),
          'reason': reason,
        },
      );
      return LeaseModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<LeaseModel>> getLeasesByStatus(LeaseStatus status) async {
    try {
      final response = await apiClient.dio.get(
        '/leases',
        queryParameters: {'status': status.name},
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) => LeaseModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<LeaseModel>> getExpiringLeases(int withinDays) async {
    try {
      final response = await apiClient.dio.get(
        '/leases/expiring',
        queryParameters: {'days': withinDays},
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) => LeaseModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<LeaseModel>> getLeasesByUnit(String unitId) async {
    try {
      final response = await apiClient.dio.get(
        '/leases',
        queryParameters: {'unit_id': unitId},
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) => LeaseModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }
}
