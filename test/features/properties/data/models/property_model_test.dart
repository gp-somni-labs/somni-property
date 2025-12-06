import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/features/properties/data/models/property_model.dart';
import 'package:somni_property/features/properties/domain/entities/property.dart';
import '../../../../fixtures/property_fixtures.dart';

void main() {
  group('PropertyModel', () {
    late PropertyModel testPropertyModel;
    late Map<String, dynamic> testJson;

    setUp(() {
      testPropertyModel = createTestPropertyModel();
      testJson = propertyJsonFixture();
    });

    test('should be a subclass of Property entity', () {
      expect(testPropertyModel, isA<Property>());
    });

    group('fromJson', () {
      test('should return a valid model when JSON is valid', () {
        final result = PropertyModel.fromJson(testJson);

        expect(result.id, testJson['id']);
        expect(result.name, testJson['name']);
        expect(result.address, testJson['address']);
        expect(result.city, testJson['city']);
        expect(result.state, testJson['state']);
        expect(result.zipCode, testJson['zip_code']);
        expect(result.type, PropertyType.apartment);
        expect(result.status, PropertyStatus.active);
        expect(result.totalUnits, testJson['total_units']);
        expect(result.occupiedUnits, testJson['occupied_units']);
        expect(result.monthlyRevenue, testJson['monthly_revenue']);
        expect(result.description, testJson['description']);
        expect(result.imageUrl, testJson['image_url']);
        expect(result.ownerId, testJson['owner_id']);
        expect(result.managerId, testJson['manager_id']);
      });

      test('should handle missing optional fields', () {
        final minimalJson = {
          'id': '1',
          'name': 'Minimal Property',
          'address': '123 St',
          'city': 'City',
          'state': 'CA',
          'zip_code': '12345',
          'type': 'singleFamily',
          'status': 'active',
          'total_units': 1,
          'owner_id': 'owner-1',
          'created_at': '2025-01-01T00:00:00.000Z',
          'updated_at': '2025-01-01T00:00:00.000Z',
        };

        final result = PropertyModel.fromJson(minimalJson);

        expect(result.id, '1');
        expect(result.occupiedUnits, 0);
        expect(result.monthlyRevenue, null);
        expect(result.description, null);
        expect(result.imageUrl, null);
        expect(result.managerId, null);
      });

      test('should use default values for invalid enum types', () {
        final jsonWithInvalidEnum = {
          ...testJson,
          'type': 'invalidType',
          'status': 'invalidStatus',
        };

        final result = PropertyModel.fromJson(jsonWithInvalidEnum);

        expect(result.type, PropertyType.singleFamily);
        expect(result.status, PropertyStatus.active);
      });

      test('should default to 1 total unit if not provided', () {
        final jsonWithoutUnits = {...testJson};
        jsonWithoutUnits.remove('total_units');

        final result = PropertyModel.fromJson(jsonWithoutUnits);

        expect(result.totalUnits, 1);
      });
    });

    group('toJson', () {
      test('should return a valid JSON map', () {
        final result = testPropertyModel.toJson();

        expect(result['id'], testPropertyModel.id);
        expect(result['name'], testPropertyModel.name);
        expect(result['address'], testPropertyModel.address);
        expect(result['city'], testPropertyModel.city);
        expect(result['state'], testPropertyModel.state);
        expect(result['zip_code'], testPropertyModel.zipCode);
        expect(result['type'], testPropertyModel.type.name);
        expect(result['status'], testPropertyModel.status.name);
        expect(result['total_units'], testPropertyModel.totalUnits);
        expect(result['occupied_units'], testPropertyModel.occupiedUnits);
        expect(result['monthly_revenue'], testPropertyModel.monthlyRevenue);
        expect(result['description'], testPropertyModel.description);
        expect(result['image_url'], testPropertyModel.imageUrl);
        expect(result['owner_id'], testPropertyModel.ownerId);
        expect(result['manager_id'], testPropertyModel.managerId);
        expect(result['created_at'], isA<String>());
        expect(result['updated_at'], isA<String>());
      });

      test('should omit null optional fields', () {
        final modelWithNulls = createTestPropertyModel(
          monthlyRevenue: null,
          description: null,
          imageUrl: null,
          managerId: null,
        );

        final result = modelWithNulls.toJson();

        expect(result.containsKey('monthly_revenue'), false);
        expect(result.containsKey('description'), false);
        expect(result.containsKey('image_url'), false);
        expect(result.containsKey('manager_id'), false);
      });

      test('should format dates as ISO 8601 strings', () {
        final result = testPropertyModel.toJson();

        expect(result['created_at'], contains('T'));
        expect(result['updated_at'], contains('T'));
        expect(() => DateTime.parse(result['created_at']), returnsNormally);
        expect(() => DateTime.parse(result['updated_at']), returnsNormally);
      });
    });

    group('fromEntity', () {
      test('should convert Property entity to PropertyModel', () {
        final entity = createTestProperty();
        final model = PropertyModel.fromEntity(entity);

        expect(model.id, entity.id);
        expect(model.name, entity.name);
        expect(model.address, entity.address);
        expect(model.city, entity.city);
        expect(model.state, entity.state);
        expect(model.zipCode, entity.zipCode);
        expect(model.type, entity.type);
        expect(model.status, entity.status);
        expect(model.totalUnits, entity.totalUnits);
        expect(model.occupiedUnits, entity.occupiedUnits);
        expect(model.monthlyRevenue, entity.monthlyRevenue);
      });
    });

    group('toEntity', () {
      test('should convert PropertyModel to Property entity', () {
        final entity = testPropertyModel.toEntity();

        expect(entity, isA<Property>());
        expect(entity.id, testPropertyModel.id);
        expect(entity.name, testPropertyModel.name);
        expect(entity.address, testPropertyModel.address);
      });
    });

    group('JSON round-trip', () {
      test('should maintain data integrity through JSON serialization', () {
        final json = testPropertyModel.toJson();
        final reconstructed = PropertyModel.fromJson(json);

        expect(reconstructed.id, testPropertyModel.id);
        expect(reconstructed.name, testPropertyModel.name);
        expect(reconstructed.address, testPropertyModel.address);
        expect(reconstructed.city, testPropertyModel.city);
        expect(reconstructed.state, testPropertyModel.state);
        expect(reconstructed.zipCode, testPropertyModel.zipCode);
        expect(reconstructed.type, testPropertyModel.type);
        expect(reconstructed.status, testPropertyModel.status);
        expect(reconstructed.totalUnits, testPropertyModel.totalUnits);
        expect(reconstructed.occupiedUnits, testPropertyModel.occupiedUnits);
        expect(reconstructed.monthlyRevenue, testPropertyModel.monthlyRevenue);
      });
    });
  });

  group('PropertyStatsModel', () {
    test('should create from JSON correctly', () {
      final json = {
        'total_properties': 5,
        'total_units': 50,
        'occupied_units': 40,
        'available_units': 10,
        'total_monthly_revenue': 75000.0,
        'average_occupancy_rate': 80.0,
      };

      final stats = PropertyStatsModel.fromJson(json);

      expect(stats.totalProperties, 5);
      expect(stats.totalUnits, 50);
      expect(stats.occupiedUnits, 40);
      expect(stats.availableUnits, 10);
      expect(stats.totalMonthlyRevenue, 75000.0);
      expect(stats.averageOccupancyRate, 80.0);
    });

    test('should use defaults for missing fields', () {
      final stats = PropertyStatsModel.fromJson({});

      expect(stats.totalProperties, 0);
      expect(stats.totalUnits, 0);
      expect(stats.occupiedUnits, 0);
      expect(stats.availableUnits, 0);
      expect(stats.totalMonthlyRevenue, 0.0);
      expect(stats.averageOccupancyRate, 0.0);
    });

    test('should calculate stats from property list', () {
      final properties = [
        createTestProperty(
          totalUnits: 10,
          occupiedUnits: 8,
          monthlyRevenue: 10000.0,
        ),
        createTestProperty(
          totalUnits: 20,
          occupiedUnits: 15,
          monthlyRevenue: 20000.0,
        ),
        createTestProperty(
          totalUnits: 30,
          occupiedUnits: 27,
          monthlyRevenue: 30000.0,
        ),
      ];

      final stats = PropertyStatsModel.fromProperties(properties);

      expect(stats.totalProperties, 3);
      expect(stats.totalUnits, 60);
      expect(stats.occupiedUnits, 50);
      expect(stats.availableUnits, 10);
      expect(stats.totalMonthlyRevenue, 60000.0);
      expect(stats.averageOccupancyRate, closeTo(83.33, 0.01));
    });

    test('should return zero stats for empty property list', () {
      final stats = PropertyStatsModel.fromProperties([]);

      expect(stats.totalProperties, 0);
      expect(stats.totalUnits, 0);
      expect(stats.occupiedUnits, 0);
      expect(stats.availableUnits, 0);
      expect(stats.totalMonthlyRevenue, 0.0);
      expect(stats.averageOccupancyRate, 0.0);
    });

    test('should handle properties with null revenue', () {
      final properties = [
        createTestProperty(monthlyRevenue: 10000.0),
        createTestProperty(monthlyRevenue: null),
        createTestProperty(monthlyRevenue: 20000.0),
      ];

      final stats = PropertyStatsModel.fromProperties(properties);

      expect(stats.totalMonthlyRevenue, 30000.0);
    });
  });
}
