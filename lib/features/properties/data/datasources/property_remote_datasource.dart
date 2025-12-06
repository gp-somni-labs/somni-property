import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/properties/data/models/property_model.dart';

/// Remote data source for properties - connects to production backend
abstract class PropertyRemoteDataSource {
  Future<List<PropertyModel>> getProperties({
    int page = 1,
    int pageSize = 50,
    String? search,
    String? type,
    String? status,
  });
  Future<PropertyModel> getPropertyById(String id);
  Future<PropertyModel> createProperty(Map<String, dynamic> data);
  Future<PropertyModel> updateProperty(String id, Map<String, dynamic> data);
  Future<void> deleteProperty(String id);
  Future<Map<String, dynamic>> getPropertyStats();
}

/// Implementation connecting to production backend
class PropertyRemoteDataSourceImpl implements PropertyRemoteDataSource {
  final ApiClient apiClient;

  PropertyRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<List<PropertyModel>> getProperties({
    int page = 1,
    int pageSize = 50,
    String? search,
    String? type,
    String? status,
  }) async {
    try {
      debugPrint('PropertyRemoteDataSource: Fetching properties (page: $page, pageSize: $pageSize)');

      // Build query parameters
      final queryParams = <String, dynamic>{
        'page': page,
        'page_size': pageSize,
      };

      if (search != null && search.isNotEmpty) {
        queryParams['search'] = search;
      }
      if (type != null && type.isNotEmpty) {
        queryParams['type'] = type;
      }
      if (status != null && status.isNotEmpty) {
        queryParams['status'] = status;
      }

      final response = await apiClient.dio.get(
        '/properties',
        queryParameters: queryParams,
      );

      debugPrint('PropertyRemoteDataSource: Received properties response: ${response.statusCode}');

      // Backend returns paginated response with items array
      final data = response.data as Map<String, dynamic>;
      final items = data['items'] as List<dynamic>?;

      if (items == null) {
        debugPrint('PropertyRemoteDataSource: No items in response, returning empty list');
        return [];
      }

      final properties = items
          .map((json) => PropertyModel.fromJson(json as Map<String, dynamic>))
          .toList();

      debugPrint('PropertyRemoteDataSource: Parsed ${properties.length} properties');
      return properties;
    } on DioException catch (e) {
      debugPrint('PropertyRemoteDataSource: Error fetching properties: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('PropertyRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to fetch properties: $e');
    }
  }

  @override
  Future<PropertyModel> getPropertyById(String id) async {
    try {
      debugPrint('PropertyRemoteDataSource: Fetching property $id');

      final response = await apiClient.dio.get('/properties/$id');

      debugPrint('PropertyRemoteDataSource: Received property detail: ${response.statusCode}');

      return PropertyModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        debugPrint('PropertyRemoteDataSource: Property $id not found');
        throw const ServerException(message: 'Property not found');
      }
      debugPrint('PropertyRemoteDataSource: Error fetching property: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('PropertyRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to fetch property: $e');
    }
  }

  @override
  Future<PropertyModel> createProperty(Map<String, dynamic> data) async {
    try {
      debugPrint('PropertyRemoteDataSource: Creating property: ${data['name']}');

      final response = await apiClient.dio.post(
        '/properties',
        data: data,
      );

      debugPrint('PropertyRemoteDataSource: Property created: ${response.statusCode}');

      return PropertyModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('PropertyRemoteDataSource: Error creating property: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('PropertyRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to create property: $e');
    }
  }

  @override
  Future<PropertyModel> updateProperty(
    String id,
    Map<String, dynamic> data,
  ) async {
    try {
      debugPrint('PropertyRemoteDataSource: Updating property $id');

      final response = await apiClient.dio.put(
        '/properties/$id',
        data: data,
      );

      debugPrint('PropertyRemoteDataSource: Property updated: ${response.statusCode}');

      return PropertyModel.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        debugPrint('PropertyRemoteDataSource: Property $id not found');
        throw const ServerException(message: 'Property not found');
      }
      debugPrint('PropertyRemoteDataSource: Error updating property: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('PropertyRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to update property: $e');
    }
  }

  @override
  Future<void> deleteProperty(String id) async {
    try {
      debugPrint('PropertyRemoteDataSource: Deleting property $id');

      await apiClient.dio.delete('/properties/$id');

      debugPrint('PropertyRemoteDataSource: Property deleted successfully');
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        debugPrint('PropertyRemoteDataSource: Property $id not found');
        throw const ServerException(message: 'Property not found');
      }
      debugPrint('PropertyRemoteDataSource: Error deleting property: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('PropertyRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to delete property: $e');
    }
  }

  @override
  Future<Map<String, dynamic>> getPropertyStats() async {
    try {
      debugPrint('PropertyRemoteDataSource: Fetching property stats');

      // Get all properties and compute stats locally for now
      // TODO: Backend should provide a dedicated stats endpoint
      final properties = await getProperties();

      int totalProperties = properties.length;
      int totalUnits = 0;
      int occupiedUnits = 0;
      double totalMonthlyRevenue = 0.0;

      for (final property in properties) {
        totalUnits += property.totalUnits ?? 0;
        occupiedUnits += property.occupiedUnits ?? 0;
        totalMonthlyRevenue += property.monthlyRevenue ?? 0.0;
      }

      final availableUnits = totalUnits - occupiedUnits;
      final averageOccupancyRate = totalUnits > 0
          ? (occupiedUnits / totalUnits * 100).roundToDouble()
          : 0.0;

      debugPrint('PropertyRemoteDataSource: Computed stats - Total: $totalProperties, Units: $totalUnits, Occupied: $occupiedUnits');

      return {
        'total_properties': totalProperties,
        'total_units': totalUnits,
        'occupied_units': occupiedUnits,
        'available_units': availableUnits,
        'total_monthly_revenue': totalMonthlyRevenue,
        'average_occupancy_rate': averageOccupancyRate,
      };
    } catch (e) {
      debugPrint('PropertyRemoteDataSource: Error fetching stats: $e');
      throw ServerException(message: 'Failed to fetch property stats: $e');
    }
  }
}
