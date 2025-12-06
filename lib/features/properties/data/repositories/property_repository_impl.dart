import 'package:dartz/dartz.dart';
import 'package:flutter/foundation.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/properties/data/datasources/property_local_datasource.dart';
import 'package:somni_property/features/properties/data/datasources/property_remote_datasource.dart';
import 'package:somni_property/features/properties/data/models/property_model.dart';
import 'package:somni_property/features/properties/domain/entities/property.dart';
import 'package:somni_property/features/properties/domain/repositories/property_repository.dart';

/// Implementation of PropertyRepository
/// Supports both local (mock) and remote (production API) data sources
class PropertyRepositoryImpl implements PropertyRepository {
  final PropertyLocalDataSource localDataSource;
  final PropertyRemoteDataSource? remoteDataSource;
  final bool useRemoteApi;

  PropertyRepositoryImpl({
    required this.localDataSource,
    this.remoteDataSource,
    this.useRemoteApi = false, // Default to mock data for development
  });

  @override
  Future<Either<Failure, List<Property>>> getProperties({
    PropertyType? typeFilter,
    PropertyStatus? statusFilter,
    String? searchQuery,
  }) async {
    try {
      List<PropertyModel> properties;

      if (useRemoteApi && remoteDataSource != null) {
        debugPrint('PropertyRepository: Using remote API datasource');
        // Use remote API with filters passed directly
        properties = await remoteDataSource!.getProperties(
          search: searchQuery,
          type: typeFilter?.name,
          status: statusFilter?.name,
        );
      } else {
        debugPrint('PropertyRepository: Using local mock datasource');
        // Use local mock data with client-side filtering
        properties = await localDataSource.getProperties();

        // Apply filters
        if (typeFilter != null) {
          properties = properties.where((p) => p.type == typeFilter).toList();
        }

        if (statusFilter != null) {
          properties = properties.where((p) => p.status == statusFilter).toList();
        }

        if (searchQuery != null && searchQuery.isNotEmpty) {
          final query = searchQuery.toLowerCase();
          properties = properties.where((p) {
            return p.name.toLowerCase().contains(query) ||
                p.address.toLowerCase().contains(query) ||
                p.city.toLowerCase().contains(query);
          }).toList();
        }
      }

      return Right(properties.map((m) => m.toEntity()).toList());
    } catch (e) {
      debugPrint('PropertyRepository: getProperties error: $e');
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Property>> getPropertyById(String id) async {
    try {
      PropertyModel? property;

      if (useRemoteApi && remoteDataSource != null) {
        debugPrint('PropertyRepository: Fetching property $id from remote API');
        property = await remoteDataSource!.getPropertyById(id);
      } else {
        debugPrint('PropertyRepository: Fetching property $id from local datasource');
        property = await localDataSource.getPropertyById(id);
      }

      if (property == null) {
        return const Left(ServerFailure(message: 'Property not found'));
      }
      return Right(property.toEntity());
    } catch (e) {
      debugPrint('PropertyRepository: getPropertyById error: $e');
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Property>> createProperty(
    CreatePropertyParams params,
  ) async {
    try {
      PropertyModel property;

      if (useRemoteApi && remoteDataSource != null) {
        debugPrint('PropertyRepository: Creating property via remote API');
        property = await remoteDataSource!.createProperty(params.toJson());
      } else {
        debugPrint('PropertyRepository: Creating property via local datasource');
        property = await localDataSource.createProperty(params.toJson());
      }

      return Right(property.toEntity());
    } catch (e) {
      debugPrint('PropertyRepository: createProperty error: $e');
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Property>> updateProperty(
    String id,
    UpdatePropertyParams params,
  ) async {
    try {
      PropertyModel property;

      if (useRemoteApi && remoteDataSource != null) {
        debugPrint('PropertyRepository: Updating property $id via remote API');
        property = await remoteDataSource!.updateProperty(id, params.toJson());
      } else {
        debugPrint('PropertyRepository: Updating property $id via local datasource');
        property = await localDataSource.updateProperty(id, params.toJson());
      }

      return Right(property.toEntity());
    } catch (e) {
      debugPrint('PropertyRepository: updateProperty error: $e');
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> deleteProperty(String id) async {
    try {
      if (useRemoteApi && remoteDataSource != null) {
        debugPrint('PropertyRepository: Deleting property $id via remote API');
        await remoteDataSource!.deleteProperty(id);
      } else {
        debugPrint('PropertyRepository: Deleting property $id via local datasource');
        await localDataSource.deleteProperty(id);
      }

      return const Right(null);
    } catch (e) {
      debugPrint('PropertyRepository: deleteProperty error: $e');
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Property>>> getPropertiesByOwner(
    String ownerId,
  ) async {
    try {
      final allProperties = await localDataSource.getProperties();
      final filtered = allProperties.where((p) => p.ownerId == ownerId).toList();
      return Right(filtered.map((m) => m.toEntity()).toList());
    } catch (e) {
      debugPrint('PropertyRepository: getPropertiesByOwner error: $e');
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Property>>> getPropertiesByManager(
    String managerId,
  ) async {
    try {
      final allProperties = await localDataSource.getProperties();
      final filtered =
          allProperties.where((p) => p.managerId == managerId).toList();
      return Right(filtered.map((m) => m.toEntity()).toList());
    } catch (e) {
      debugPrint('PropertyRepository: getPropertiesByManager error: $e');
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, PropertyStats>> getPropertyStats() async {
    try {
      if (useRemoteApi && remoteDataSource != null) {
        debugPrint('PropertyRepository: Fetching stats from remote API');
        final statsData = await remoteDataSource!.getPropertyStats();

        return Right(PropertyStats(
          totalProperties: statsData['total_properties'] as int? ?? 0,
          totalUnits: statsData['total_units'] as int? ?? 0,
          occupiedUnits: statsData['occupied_units'] as int? ?? 0,
          availableUnits: statsData['available_units'] as int? ?? 0,
          totalMonthlyRevenue: (statsData['total_monthly_revenue'] as num?)?.toDouble() ?? 0.0,
          averageOccupancyRate: (statsData['average_occupancy_rate'] as num?)?.toDouble() ?? 0.0,
        ));
      } else {
        debugPrint('PropertyRepository: Computing stats from local datasource');
        final properties = await localDataSource.getProperties();
        final stats = PropertyStatsModel.fromProperties(properties);
        return Right(PropertyStats(
          totalProperties: stats.totalProperties,
          totalUnits: stats.totalUnits,
          occupiedUnits: stats.occupiedUnits,
          availableUnits: stats.availableUnits,
          totalMonthlyRevenue: stats.totalMonthlyRevenue,
          averageOccupancyRate: stats.averageOccupancyRate,
        ));
      }
    } catch (e) {
      debugPrint('PropertyRepository: getPropertyStats error: $e');
      return Left(ServerFailure(message: e.toString()));
    }
  }
}
