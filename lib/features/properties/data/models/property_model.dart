import 'package:somni_property/features/properties/domain/entities/property.dart';

/// Property model for JSON serialization
class PropertyModel extends Property {
  const PropertyModel({
    required super.id,
    required super.name,
    required super.address,
    required super.city,
    required super.state,
    required super.zipCode,
    required super.type,
    required super.status,
    required super.totalUnits,
    super.occupiedUnits,
    super.monthlyRevenue,
    super.description,
    super.imageUrl,
    required super.ownerId,
    super.managerId,
    required super.createdAt,
    required super.updatedAt,
  });

  factory PropertyModel.fromJson(Map<String, dynamic> json) {
    return PropertyModel(
      id: json['id'] as String,
      name: json['name'] as String,
      address: json['address'] as String,
      city: json['city'] as String,
      state: json['state'] as String,
      zipCode: json['zip_code'] as String,
      type: PropertyType.values.firstWhere(
        (t) => t.name == json['type'],
        orElse: () => PropertyType.singleFamily,
      ),
      status: PropertyStatus.values.firstWhere(
        (s) => s.name == json['status'],
        orElse: () => PropertyStatus.active,
      ),
      totalUnits: json['total_units'] as int? ?? 1,
      occupiedUnits: json['occupied_units'] as int? ?? 0,
      monthlyRevenue: (json['monthly_revenue'] as num?)?.toDouble(),
      description: json['description'] as String?,
      imageUrl: json['image_url'] as String?,
      ownerId: json['owner_id'] as String,
      managerId: json['manager_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'address': address,
      'city': city,
      'state': state,
      'zip_code': zipCode,
      'type': type.name,
      'status': status.name,
      'total_units': totalUnits,
      'occupied_units': occupiedUnits,
      if (monthlyRevenue != null) 'monthly_revenue': monthlyRevenue,
      if (description != null) 'description': description,
      if (imageUrl != null) 'image_url': imageUrl,
      'owner_id': ownerId,
      if (managerId != null) 'manager_id': managerId,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  /// Convert entity to model
  factory PropertyModel.fromEntity(Property property) {
    return PropertyModel(
      id: property.id,
      name: property.name,
      address: property.address,
      city: property.city,
      state: property.state,
      zipCode: property.zipCode,
      type: property.type,
      status: property.status,
      totalUnits: property.totalUnits,
      occupiedUnits: property.occupiedUnits,
      monthlyRevenue: property.monthlyRevenue,
      description: property.description,
      imageUrl: property.imageUrl,
      ownerId: property.ownerId,
      managerId: property.managerId,
      createdAt: property.createdAt,
      updatedAt: property.updatedAt,
    );
  }

  /// Convert to domain entity
  Property toEntity() => this;
}

/// Property statistics model
class PropertyStatsModel {
  final int totalProperties;
  final int totalUnits;
  final int occupiedUnits;
  final int availableUnits;
  final double totalMonthlyRevenue;
  final double averageOccupancyRate;

  const PropertyStatsModel({
    required this.totalProperties,
    required this.totalUnits,
    required this.occupiedUnits,
    required this.availableUnits,
    required this.totalMonthlyRevenue,
    required this.averageOccupancyRate,
  });

  factory PropertyStatsModel.fromJson(Map<String, dynamic> json) {
    return PropertyStatsModel(
      totalProperties: json['total_properties'] as int? ?? 0,
      totalUnits: json['total_units'] as int? ?? 0,
      occupiedUnits: json['occupied_units'] as int? ?? 0,
      availableUnits: json['available_units'] as int? ?? 0,
      totalMonthlyRevenue:
          (json['total_monthly_revenue'] as num?)?.toDouble() ?? 0.0,
      averageOccupancyRate:
          (json['average_occupancy_rate'] as num?)?.toDouble() ?? 0.0,
    );
  }

  /// Calculate from list of properties
  factory PropertyStatsModel.fromProperties(List<Property> properties) {
    if (properties.isEmpty) {
      return const PropertyStatsModel(
        totalProperties: 0,
        totalUnits: 0,
        occupiedUnits: 0,
        availableUnits: 0,
        totalMonthlyRevenue: 0,
        averageOccupancyRate: 0,
      );
    }

    final totalUnits =
        properties.fold<int>(0, (sum, p) => sum + p.totalUnits);
    final occupiedUnits =
        properties.fold<int>(0, (sum, p) => sum + p.occupiedUnits);
    final totalRevenue =
        properties.fold<double>(0, (sum, p) => sum + (p.monthlyRevenue ?? 0));

    return PropertyStatsModel(
      totalProperties: properties.length,
      totalUnits: totalUnits,
      occupiedUnits: occupiedUnits,
      availableUnits: totalUnits - occupiedUnits,
      totalMonthlyRevenue: totalRevenue,
      averageOccupancyRate:
          totalUnits > 0 ? (occupiedUnits / totalUnits) * 100 : 0,
    );
  }
}
