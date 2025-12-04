import 'package:equatable/equatable.dart';

/// Property entity representing a real estate property
class Property extends Equatable {
  final String id;
  final String name;
  final String address;
  final String city;
  final String state;
  final String zipCode;
  final PropertyType type;
  final PropertyStatus status;
  final int totalUnits;
  final int occupiedUnits;
  final double? monthlyRevenue;
  final String? description;
  final String? imageUrl;
  final String ownerId;
  final String? managerId;
  final DateTime createdAt;
  final DateTime updatedAt;

  const Property({
    required this.id,
    required this.name,
    required this.address,
    required this.city,
    required this.state,
    required this.zipCode,
    required this.type,
    required this.status,
    required this.totalUnits,
    this.occupiedUnits = 0,
    this.monthlyRevenue,
    this.description,
    this.imageUrl,
    required this.ownerId,
    this.managerId,
    required this.createdAt,
    required this.updatedAt,
  });

  /// Calculate occupancy rate as a percentage
  double get occupancyRate {
    if (totalUnits == 0) return 0;
    return (occupiedUnits / totalUnits) * 100;
  }

  /// Get available units count
  int get availableUnits => totalUnits - occupiedUnits;

  /// Check if property is fully occupied
  bool get isFullyOccupied => occupiedUnits >= totalUnits;

  /// Get formatted full address
  String get fullAddress => '$address, $city, $state $zipCode';

  @override
  List<Object?> get props => [
        id,
        name,
        address,
        city,
        state,
        zipCode,
        type,
        status,
        totalUnits,
        occupiedUnits,
        monthlyRevenue,
        description,
        imageUrl,
        ownerId,
        managerId,
        createdAt,
        updatedAt,
      ];

  Property copyWith({
    String? id,
    String? name,
    String? address,
    String? city,
    String? state,
    String? zipCode,
    PropertyType? type,
    PropertyStatus? status,
    int? totalUnits,
    int? occupiedUnits,
    double? monthlyRevenue,
    String? description,
    String? imageUrl,
    String? ownerId,
    String? managerId,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Property(
      id: id ?? this.id,
      name: name ?? this.name,
      address: address ?? this.address,
      city: city ?? this.city,
      state: state ?? this.state,
      zipCode: zipCode ?? this.zipCode,
      type: type ?? this.type,
      status: status ?? this.status,
      totalUnits: totalUnits ?? this.totalUnits,
      occupiedUnits: occupiedUnits ?? this.occupiedUnits,
      monthlyRevenue: monthlyRevenue ?? this.monthlyRevenue,
      description: description ?? this.description,
      imageUrl: imageUrl ?? this.imageUrl,
      ownerId: ownerId ?? this.ownerId,
      managerId: managerId ?? this.managerId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

/// Types of properties
enum PropertyType {
  singleFamily('Single Family'),
  multiFamily('Multi-Family'),
  apartment('Apartment'),
  condo('Condo'),
  townhouse('Townhouse'),
  commercial('Commercial'),
  industrial('Industrial'),
  mixed('Mixed Use');

  final String displayName;
  const PropertyType(this.displayName);
}

/// Property status
enum PropertyStatus {
  active('Active'),
  inactive('Inactive'),
  maintenance('Under Maintenance'),
  listed('Listed for Sale'),
  pending('Pending');

  final String displayName;
  const PropertyStatus(this.displayName);
}
