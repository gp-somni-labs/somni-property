import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/tenants/data/models/tenant_model.dart';
import 'package:somni_property/features/tenants/domain/entities/tenant.dart';

/// Provider for tenant remote data source
final tenantRemoteDataSourceProvider = Provider<TenantRemoteDataSource>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return TenantRemoteDataSourceImpl(apiClient: apiClient);
});

/// Abstract interface for tenant remote operations
abstract class TenantRemoteDataSource {
  Future<List<TenantModel>> getTenants({String? propertyId});
  Future<TenantModel> getTenant(String id);
  Future<TenantModel> createTenant(TenantModel tenant);
  Future<TenantModel> updateTenant(TenantModel tenant);
  Future<void> deleteTenant(String id);
  Future<List<TenantModel>> searchTenants(String query);
  Future<List<TenantModel>> getTenantsByUnit(String unitId);
  Future<List<TenantModel>> getTenantsByStatus(TenantStatus status);
}

/// Implementation of tenant remote data source
class TenantRemoteDataSourceImpl implements TenantRemoteDataSource {
  final ApiClient apiClient;

  TenantRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<List<TenantModel>> getTenants({String? propertyId}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (propertyId != null) {
        queryParams['property_id'] = propertyId;
      }

      final response = await apiClient.dio.get(
        '/tenants',
        queryParameters: queryParams.isNotEmpty ? queryParams : null,
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) => TenantModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<TenantModel> getTenant(String id) async {
    try {
      final response = await apiClient.dio.get('/tenants/$id');
      return TenantModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<TenantModel> createTenant(TenantModel tenant) async {
    try {
      final response = await apiClient.dio.post(
        '/tenants',
        data: tenant.toCreateJson(),
      );
      return TenantModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<TenantModel> updateTenant(TenantModel tenant) async {
    try {
      final response = await apiClient.dio.put(
        '/tenants/${tenant.id}',
        data: tenant.toJson(),
      );
      return TenantModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<void> deleteTenant(String id) async {
    try {
      await apiClient.dio.delete('/tenants/$id');
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<TenantModel>> searchTenants(String query) async {
    try {
      final response = await apiClient.dio.get(
        '/tenants/search',
        queryParameters: {'q': query},
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) => TenantModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<TenantModel>> getTenantsByUnit(String unitId) async {
    try {
      final response = await apiClient.dio.get(
        '/tenants',
        queryParameters: {'unit_id': unitId},
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) => TenantModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<TenantModel>> getTenantsByStatus(TenantStatus status) async {
    try {
      final response = await apiClient.dio.get(
        '/tenants',
        queryParameters: {'status': status.name},
      );

      final data = response.data as List<dynamic>;
      return data
          .map((json) => TenantModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }
}
