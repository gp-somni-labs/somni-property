import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/features/properties/domain/entities/property.dart';
import '../../../../fixtures/property_fixtures.dart';

void main() {
  group('Property Entity', () {
    late Property testProperty;

    setUp(() {
      testProperty = createTestProperty(
        totalUnits: 20,
        occupiedUnits: 15,
        monthlyRevenue: 30000.0,
      );
    });

    test('should calculate correct occupancy rate', () {
      expect(testProperty.occupancyRate, 75.0);
    });

    test('should calculate correct occupancy rate when fully occupied', () {
      final property = testProperty.copyWith(occupiedUnits: 20);
      expect(property.occupancyRate, 100.0);
    });

    test('should return 0 occupancy rate when no units', () {
      final property = testProperty.copyWith(totalUnits: 0, occupiedUnits: 0);
      expect(property.occupancyRate, 0.0);
    });

    test('should calculate correct available units', () {
      expect(testProperty.availableUnits, 5);
    });

    test('should correctly identify if fully occupied', () {
      expect(testProperty.isFullyOccupied, false);

      final occupied = testProperty.copyWith(occupiedUnits: 20);
      expect(occupied.isFullyOccupied, true);
    });

    test('should format full address correctly', () {
      expect(
        testProperty.fullAddress,
        '123 Main St, Test City, CA 12345',
      );
    });

    test('should create copy with new values', () {
      final updated = testProperty.copyWith(
        name: 'Updated Property',
        monthlyRevenue: 35000.0,
      );

      expect(updated.name, 'Updated Property');
      expect(updated.monthlyRevenue, 35000.0);
      expect(updated.id, testProperty.id);
      expect(updated.address, testProperty.address);
    });

    test('should support equality comparison', () {
      final property1 = createTestProperty(id: 'prop-1');
      final property2 = createTestProperty(id: 'prop-1');
      final property3 = createTestProperty(id: 'prop-2');

      expect(property1, equals(property2));
      expect(property1, isNot(equals(property3)));
    });
  });

  group('PropertyType Enum', () {
    test('should have correct display names', () {
      expect(PropertyType.singleFamily.displayName, 'Single Family');
      expect(PropertyType.multiFamily.displayName, 'Multi-Family');
      expect(PropertyType.apartment.displayName, 'Apartment');
      expect(PropertyType.condo.displayName, 'Condo');
      expect(PropertyType.townhouse.displayName, 'Townhouse');
      expect(PropertyType.commercial.displayName, 'Commercial');
      expect(PropertyType.industrial.displayName, 'Industrial');
      expect(PropertyType.mixed.displayName, 'Mixed Use');
    });

    test('should have all enum values', () {
      expect(PropertyType.values.length, 8);
    });
  });

  group('PropertyStatus Enum', () {
    test('should have correct display names', () {
      expect(PropertyStatus.active.displayName, 'Active');
      expect(PropertyStatus.inactive.displayName, 'Inactive');
      expect(PropertyStatus.maintenance.displayName, 'Under Maintenance');
      expect(PropertyStatus.listed.displayName, 'Listed for Sale');
      expect(PropertyStatus.pending.displayName, 'Pending');
    });

    test('should have all enum values', () {
      expect(PropertyStatus.values.length, 5);
    });
  });
}
