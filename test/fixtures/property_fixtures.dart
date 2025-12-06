import 'package:somni_property/features/properties/domain/entities/property.dart';
import 'package:somni_property/features/properties/data/models/property_model.dart';

/// Test fixture for Property entity
Property createTestProperty({
  String id = 'test-property-1',
  String name = 'Test Property',
  String address = '123 Main St',
  String city = 'Test City',
  String state = 'CA',
  String zipCode = '12345',
  PropertyType type = PropertyType.apartment,
  PropertyStatus status = PropertyStatus.active,
  int totalUnits = 10,
  int occupiedUnits = 7,
  double? monthlyRevenue = 15000.0,
  String? description = 'A test property',
  String? imageUrl,
  String ownerId = 'owner-1',
  String? managerId = 'manager-1',
  DateTime? createdAt,
  DateTime? updatedAt,
}) {
  final now = DateTime.now();
  return Property(
    id: id,
    name: name,
    address: address,
    city: city,
    state: state,
    zipCode: zipCode,
    type: type,
    status: status,
    totalUnits: totalUnits,
    occupiedUnits: occupiedUnits,
    monthlyRevenue: monthlyRevenue,
    description: description,
    imageUrl: imageUrl,
    ownerId: ownerId,
    managerId: managerId,
    createdAt: createdAt ?? now,
    updatedAt: updatedAt ?? now,
  );
}

/// Test fixture for PropertyModel
PropertyModel createTestPropertyModel({
  String id = 'test-property-1',
  String name = 'Test Property',
  String address = '123 Main St',
  String city = 'Test City',
  String state = 'CA',
  String zipCode = '12345',
  PropertyType type = PropertyType.apartment,
  PropertyStatus status = PropertyStatus.active,
  int totalUnits = 10,
  int occupiedUnits = 7,
  double? monthlyRevenue = 15000.0,
  String? description = 'A test property',
  String? imageUrl,
  String ownerId = 'owner-1',
  String? managerId = 'manager-1',
  DateTime? createdAt,
  DateTime? updatedAt,
}) {
  final now = DateTime.now();
  return PropertyModel(
    id: id,
    name: name,
    address: address,
    city: city,
    state: state,
    zipCode: zipCode,
    type: type,
    status: status,
    totalUnits: totalUnits,
    occupiedUnits: occupiedUnits,
    monthlyRevenue: monthlyRevenue,
    description: description,
    imageUrl: imageUrl,
    ownerId: ownerId,
    managerId: managerId,
    createdAt: createdAt ?? now,
    updatedAt: updatedAt ?? now,
  );
}

/// Sample JSON response for property
Map<String, dynamic> propertyJsonFixture({
  String id = 'test-property-1',
  String name = 'Test Property',
}) {
  return {
    'id': id,
    'name': name,
    'address': '123 Main St',
    'city': 'Test City',
    'state': 'CA',
    'zip_code': '12345',
    'type': 'apartment',
    'status': 'active',
    'total_units': 10,
    'occupied_units': 7,
    'monthly_revenue': 15000.0,
    'description': 'A test property',
    'image_url': 'https://example.com/image.jpg',
    'owner_id': 'owner-1',
    'manager_id': 'manager-1',
    'created_at': '2025-01-01T00:00:00.000Z',
    'updated_at': '2025-01-01T00:00:00.000Z',
  };
}

/// List of test properties
List<Property> createTestPropertiesList({int count = 3}) {
  return List.generate(
    count,
    (index) => createTestProperty(
      id: 'property-$index',
      name: 'Property $index',
      occupiedUnits: 5 + index,
    ),
  );
}
