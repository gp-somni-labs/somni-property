import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/properties/domain/entities/property.dart';

/// Repository interface for property operations
abstract class PropertyRepository {
  /// Get all properties accessible to the current user
  Future<Either<Failure, List<Property>>> getProperties({
    PropertyType? typeFilter,
    PropertyStatus? statusFilter,
    String? searchQuery,
  });

  /// Get a single property by ID
  Future<Either<Failure, Property>> getPropertyById(String id);

  /// Create a new property
  Future<Either<Failure, Property>> createProperty(CreatePropertyParams params);

  /// Update an existing property
  Future<Either<Failure, Property>> updateProperty(
    String id,
    UpdatePropertyParams params,
  );

  /// Delete a property
  Future<Either<Failure, void>> deleteProperty(String id);

  /// Get properties by owner ID
  Future<Either<Failure, List<Property>>> getPropertiesByOwner(String ownerId);

  /// Get properties by manager ID
  Future<Either<Failure, List<Property>>> getPropertiesByManager(String managerId);

  /// Get property statistics (total, occupied, available units)
  Future<Either<Failure, PropertyStats>> getPropertyStats();
}

/// Parameters for creating a new property
class CreatePropertyParams {
  final String name;
  final String address;
  final String city;
  final String state;
  final String zipCode;
  final PropertyType type;
  final int totalUnits;
  final String? description;
  final String? managerId;

  const CreatePropertyParams({
    required this.name,
    required this.address,
    required this.city,
    required this.state,
    required this.zipCode,
    required this.type,
    required this.totalUnits,
    this.description,
    this.managerId,
  });

  Map<String, dynamic> toJson() => {
        'name': name,
        'address': address,
        'city': city,
        'state': state,
        'zip_code': zipCode,
        'type': type.name,
        'total_units': totalUnits,
        if (description != null) 'description': description,
        if (managerId != null) 'manager_id': managerId,
      };
}

/// Parameters for updating a property
class UpdatePropertyParams {
  final String? name;
  final String? address;
  final String? city;
  final String? state;
  final String? zipCode;
  final PropertyType? type;
  final PropertyStatus? status;
  final int? totalUnits;
  final String? description;
  final String? managerId;

  const UpdatePropertyParams({
    this.name,
    this.address,
    this.city,
    this.state,
    this.zipCode,
    this.type,
    this.status,
    this.totalUnits,
    this.description,
    this.managerId,
  });

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{};
    if (name != null) map['name'] = name;
    if (address != null) map['address'] = address;
    if (city != null) map['city'] = city;
    if (state != null) map['state'] = state;
    if (zipCode != null) map['zip_code'] = zipCode;
    if (type != null) map['type'] = type!.name;
    if (status != null) map['status'] = status!.name;
    if (totalUnits != null) map['total_units'] = totalUnits;
    if (description != null) map['description'] = description;
    if (managerId != null) map['manager_id'] = managerId;
    return map;
  }
}

/// Property statistics
class PropertyStats {
  final int totalProperties;
  final int totalUnits;
  final int occupiedUnits;
  final int availableUnits;
  final double totalMonthlyRevenue;
  final double averageOccupancyRate;

  const PropertyStats({
    required this.totalProperties,
    required this.totalUnits,
    required this.occupiedUnits,
    required this.availableUnits,
    required this.totalMonthlyRevenue,
    required this.averageOccupancyRate,
  });
}
