import 'package:flutter/foundation.dart';
import 'package:somni_property/features/properties/data/models/property_model.dart';
import 'package:somni_property/features/properties/domain/entities/property.dart';

/// Local data source for properties (mock data for initial development)
/// Will be replaced with API calls once backend is ready
abstract class PropertyLocalDataSource {
  Future<List<PropertyModel>> getProperties();
  Future<PropertyModel?> getPropertyById(String id);
  Future<PropertyModel> createProperty(Map<String, dynamic> data);
  Future<PropertyModel> updateProperty(String id, Map<String, dynamic> data);
  Future<void> deleteProperty(String id);
}

/// Mock implementation with sample data
class PropertyLocalDataSourceImpl implements PropertyLocalDataSource {
  // In-memory storage for mock data
  final Map<String, PropertyModel> _properties = {};

  PropertyLocalDataSourceImpl() {
    _initializeMockData();
  }

  void _initializeMockData() {
    final now = DateTime.now();
    final mockProperties = [
      PropertyModel(
        id: 'prop-001',
        name: 'Sunset Apartments',
        address: '123 Main Street',
        city: 'Austin',
        state: 'TX',
        zipCode: '78701',
        type: PropertyType.apartment,
        status: PropertyStatus.active,
        totalUnits: 24,
        occupiedUnits: 22,
        monthlyRevenue: 28600,
        description: 'Modern apartment complex in downtown Austin with amenities including pool, gym, and parking.',
        ownerId: 'admin',
        managerId: 'manager-001',
        createdAt: now.subtract(const Duration(days: 365)),
        updatedAt: now.subtract(const Duration(days: 5)),
      ),
      PropertyModel(
        id: 'prop-002',
        name: 'Oak Park Townhomes',
        address: '456 Oak Lane',
        city: 'Round Rock',
        state: 'TX',
        zipCode: '78664',
        type: PropertyType.townhouse,
        status: PropertyStatus.active,
        totalUnits: 12,
        occupiedUnits: 10,
        monthlyRevenue: 18500,
        description: 'Family-friendly townhome community with excellent schools nearby.',
        ownerId: 'admin',
        managerId: 'manager-001',
        createdAt: now.subtract(const Duration(days: 200)),
        updatedAt: now.subtract(const Duration(days: 10)),
      ),
      PropertyModel(
        id: 'prop-003',
        name: 'Riverside Single Family',
        address: '789 River Road',
        city: 'Pflugerville',
        state: 'TX',
        zipCode: '78660',
        type: PropertyType.singleFamily,
        status: PropertyStatus.active,
        totalUnits: 1,
        occupiedUnits: 1,
        monthlyRevenue: 2200,
        description: '3 bedroom, 2 bath single family home with large backyard.',
        ownerId: 'admin',
        createdAt: now.subtract(const Duration(days: 150)),
        updatedAt: now.subtract(const Duration(days: 30)),
      ),
      PropertyModel(
        id: 'prop-004',
        name: 'Downtown Lofts',
        address: '101 Congress Ave',
        city: 'Austin',
        state: 'TX',
        zipCode: '78701',
        type: PropertyType.condo,
        status: PropertyStatus.active,
        totalUnits: 8,
        occupiedUnits: 6,
        monthlyRevenue: 14400,
        description: 'Luxury loft condos in the heart of downtown Austin.',
        ownerId: 'admin',
        managerId: 'manager-002',
        createdAt: now.subtract(const Duration(days: 90)),
        updatedAt: now.subtract(const Duration(days: 2)),
      ),
      PropertyModel(
        id: 'prop-005',
        name: 'Tech Park Office Complex',
        address: '500 Innovation Drive',
        city: 'Cedar Park',
        state: 'TX',
        zipCode: '78613',
        type: PropertyType.commercial,
        status: PropertyStatus.maintenance,
        totalUnits: 20,
        occupiedUnits: 15,
        monthlyRevenue: 45000,
        description: 'Class A office space near tech corridor. Currently undergoing HVAC upgrade.',
        ownerId: 'admin',
        managerId: 'manager-001',
        createdAt: now.subtract(const Duration(days: 500)),
        updatedAt: now,
      ),
      PropertyModel(
        id: 'prop-006',
        name: 'Lakeside Villas',
        address: '222 Lake Shore Blvd',
        city: 'Lakeway',
        state: 'TX',
        zipCode: '78734',
        type: PropertyType.multiFamily,
        status: PropertyStatus.active,
        totalUnits: 16,
        occupiedUnits: 16,
        monthlyRevenue: 32000,
        description: 'Fully occupied luxury villas with lake access and private docks.',
        ownerId: 'admin',
        createdAt: now.subtract(const Duration(days: 400)),
        updatedAt: now.subtract(const Duration(days: 60)),
      ),
    ];

    for (final property in mockProperties) {
      _properties[property.id] = property;
    }

    debugPrint('PropertyLocalDataSource: Initialized with ${_properties.length} mock properties');
  }

  @override
  Future<List<PropertyModel>> getProperties() async {
    // Simulate network delay
    await Future.delayed(const Duration(milliseconds: 300));
    return _properties.values.toList()
      ..sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
  }

  @override
  Future<PropertyModel?> getPropertyById(String id) async {
    await Future.delayed(const Duration(milliseconds: 200));
    return _properties[id];
  }

  @override
  Future<PropertyModel> createProperty(Map<String, dynamic> data) async {
    await Future.delayed(const Duration(milliseconds: 500));

    final now = DateTime.now();
    final id = 'prop-${now.millisecondsSinceEpoch}';

    final property = PropertyModel(
      id: id,
      name: data['name'] as String,
      address: data['address'] as String,
      city: data['city'] as String,
      state: data['state'] as String,
      zipCode: data['zip_code'] as String,
      type: PropertyType.values.firstWhere(
        (t) => t.name == data['type'],
        orElse: () => PropertyType.singleFamily,
      ),
      status: PropertyStatus.active,
      totalUnits: data['total_units'] as int? ?? 1,
      occupiedUnits: 0,
      description: data['description'] as String?,
      ownerId: data['owner_id'] as String? ?? 'admin',
      managerId: data['manager_id'] as String?,
      createdAt: now,
      updatedAt: now,
    );

    _properties[id] = property;
    debugPrint('PropertyLocalDataSource: Created property $id');

    return property;
  }

  @override
  Future<PropertyModel> updateProperty(String id, Map<String, dynamic> data) async {
    await Future.delayed(const Duration(milliseconds: 400));

    final existing = _properties[id];
    if (existing == null) {
      throw Exception('Property not found: $id');
    }

    final updated = PropertyModel(
      id: existing.id,
      name: data['name'] as String? ?? existing.name,
      address: data['address'] as String? ?? existing.address,
      city: data['city'] as String? ?? existing.city,
      state: data['state'] as String? ?? existing.state,
      zipCode: data['zip_code'] as String? ?? existing.zipCode,
      type: data['type'] != null
          ? PropertyType.values.firstWhere(
              (t) => t.name == data['type'],
              orElse: () => existing.type,
            )
          : existing.type,
      status: data['status'] != null
          ? PropertyStatus.values.firstWhere(
              (s) => s.name == data['status'],
              orElse: () => existing.status,
            )
          : existing.status,
      totalUnits: data['total_units'] as int? ?? existing.totalUnits,
      occupiedUnits: data['occupied_units'] as int? ?? existing.occupiedUnits,
      monthlyRevenue: data['monthly_revenue'] != null
          ? (data['monthly_revenue'] as num).toDouble()
          : existing.monthlyRevenue,
      description: data['description'] as String? ?? existing.description,
      imageUrl: data['image_url'] as String? ?? existing.imageUrl,
      ownerId: existing.ownerId,
      managerId: data['manager_id'] as String? ?? existing.managerId,
      createdAt: existing.createdAt,
      updatedAt: DateTime.now(),
    );

    _properties[id] = updated;
    debugPrint('PropertyLocalDataSource: Updated property $id');

    return updated;
  }

  @override
  Future<void> deleteProperty(String id) async {
    await Future.delayed(const Duration(milliseconds: 300));

    if (!_properties.containsKey(id)) {
      throw Exception('Property not found: $id');
    }

    _properties.remove(id);
    debugPrint('PropertyLocalDataSource: Deleted property $id');
  }
}
