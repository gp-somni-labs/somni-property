import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/features/tenants/domain/entities/tenant.dart';
import '../../../../fixtures/tenant_fixtures.dart';

void main() {
  group('Tenant Entity', () {
    late Tenant testTenant;

    setUp(() {
      testTenant = createTestTenant();
    });

    test('should return correct full name', () {
      expect(testTenant.fullName, 'John Doe');
    });

    test('should return correct initials', () {
      expect(testTenant.initials, 'JD');
    });

    test('should return initials for single letter names', () {
      final tenant = createTestTenant(firstName: 'J', lastName: 'D');
      expect(tenant.initials, 'JD');
    });

    test('should handle empty names for initials', () {
      final tenant = createTestTenant(firstName: '', lastName: '');
      expect(tenant.initials, '');
    });

    test('should correctly identify if tenant has active lease', () {
      expect(testTenant.hasActiveLease, true);

      final noLease = testTenant.copyWith(
        currentLeaseId: null,
        currentUnitId: null,
      );
      expect(noLease.hasActiveLease, false);
    });

    test('should format phone number correctly for 10-digit numbers', () {
      final tenant = createTestTenant(phone: '5551234567');
      expect(tenant.formattedPhone, '(555) 123-4567');
    });

    test('should return unformatted phone for non-10-digit numbers', () {
      final tenant = createTestTenant(phone: '555-123-4567');
      expect(tenant.formattedPhone, '555-123-4567');
    });

    test('should create copy with new values', () {
      final updated = testTenant.copyWith(
        firstName: 'Jane',
        status: TenantStatus.inactive,
        currentLeaseId: 'new-lease',
      );

      expect(updated.firstName, 'Jane');
      expect(updated.status, TenantStatus.inactive);
      expect(updated.currentLeaseId, 'new-lease');
      expect(updated.id, testTenant.id);
      expect(updated.email, testTenant.email);
    });

    test('should support equality comparison', () {
      final tenant1 = createTestTenant(id: 'tenant-1');
      final tenant2 = createTestTenant(id: 'tenant-1');
      final tenant3 = createTestTenant(id: 'tenant-2');

      expect(tenant1, equals(tenant2));
      expect(tenant1, isNot(equals(tenant3)));
    });

    test('should include emergency contact in props', () {
      final contact1 = createTestEmergencyContact(name: 'Contact1');
      final contact2 = createTestEmergencyContact(name: 'Contact2');

      final tenant1 = createTestTenant(emergencyContact: contact1);
      final tenant2 = createTestTenant(emergencyContact: contact2);

      expect(tenant1, isNot(equals(tenant2)));
    });
  });

  group('TenantStatus Enum', () {
    test('should have correct display names', () {
      expect(TenantStatus.active.displayName, 'Active');
      expect(TenantStatus.inactive.displayName, 'Inactive');
      expect(TenantStatus.pending.displayName, 'Pending');
      expect(TenantStatus.evicted.displayName, 'Evicted');
      expect(TenantStatus.movedOut.displayName, 'Moved Out');
    });

    test('should have all enum values', () {
      expect(TenantStatus.values.length, 5);
    });
  });

  group('EmergencyContact', () {
    test('should create emergency contact correctly', () {
      final contact = createTestEmergencyContact(
        name: 'Jane Doe',
        phone: '1234567890',
        relationship: 'Spouse',
      );

      expect(contact.name, 'Jane Doe');
      expect(contact.phone, '1234567890');
      expect(contact.relationship, 'Spouse');
    });

    test('should support equality comparison', () {
      final contact1 = createTestEmergencyContact(name: 'Jane');
      final contact2 = createTestEmergencyContact(name: 'Jane');
      final contact3 = createTestEmergencyContact(name: 'John');

      expect(contact1, equals(contact2));
      expect(contact1, isNot(equals(contact3)));
    });

    test('should serialize to JSON correctly', () {
      final contact = createTestEmergencyContact();
      final json = contact.toJson();

      expect(json['name'], contact.name);
      expect(json['phone'], contact.phone);
      expect(json['relationship'], contact.relationship);
    });

    test('should deserialize from JSON correctly', () {
      final json = {
        'name': 'Test Contact',
        'phone': '5551234567',
        'relationship': 'Parent',
      };

      final contact = EmergencyContact.fromJson(json);

      expect(contact.name, 'Test Contact');
      expect(contact.phone, '5551234567');
      expect(contact.relationship, 'Parent');
    });

    test('should maintain data through JSON round-trip', () {
      final original = createTestEmergencyContact();
      final json = original.toJson();
      final reconstructed = EmergencyContact.fromJson(json);

      expect(reconstructed, equals(original));
    });
  });
}
