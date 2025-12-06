import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/features/tenants/data/models/tenant_model.dart';
import 'package:somni_property/features/tenants/domain/entities/tenant.dart';
import '../../../../fixtures/tenant_fixtures.dart';

void main() {
  group('TenantModel', () {
    late Map<String, dynamic> testJson;

    setUp(() {
      testJson = tenantJsonFixture();
    });

    test('should be a subclass of Tenant entity', () {
      final model = TenantModel.fromJson(testJson);
      expect(model, isA<Tenant>());
    });

    group('fromJson', () {
      test('should return a valid model when JSON is valid', () {
        final result = TenantModel.fromJson(testJson);

        expect(result.id, testJson['id']);
        expect(result.firstName, testJson['first_name']);
        expect(result.lastName, testJson['last_name']);
        expect(result.email, testJson['email']);
        expect(result.phone, testJson['phone']);
        expect(result.dateOfBirth, testJson['date_of_birth']);
        expect(result.currentUnitId, testJson['current_unit_id']);
        expect(result.currentLeaseId, testJson['current_lease_id']);
        expect(result.status, TenantStatus.active);
        expect(result.notes, testJson['notes']);
        expect(result.profileImageUrl, testJson['profile_image_url']);
        expect(result.emergencyContact, isNotNull);
      });

      test('should handle missing optional fields', () {
        final minimalJson = {
          'id': '1',
          'first_name': 'John',
          'last_name': 'Doe',
          'email': 'john@example.com',
          'phone': '1234567890',
          'status': 'active',
          'created_at': '2025-01-01T00:00:00.000Z',
          'updated_at': '2025-01-01T00:00:00.000Z',
        };

        final result = TenantModel.fromJson(minimalJson);

        expect(result.id, '1');
        expect(result.dateOfBirth, null);
        expect(result.emergencyContact, null);
        expect(result.currentUnitId, null);
        expect(result.currentLeaseId, null);
        expect(result.notes, null);
        expect(result.profileImageUrl, null);
      });

      test('should use default values for missing required fields', () {
        final emptyJson = <String, dynamic>{};

        final result = TenantModel.fromJson(emptyJson);

        expect(result.id, '');
        expect(result.firstName, '');
        expect(result.lastName, '');
        expect(result.email, '');
        expect(result.phone, '');
        expect(result.status, TenantStatus.active);
      });

      test('should use default status for invalid status value', () {
        final jsonWithInvalidStatus = {
          ...testJson,
          'status': 'invalidStatus',
        };

        final result = TenantModel.fromJson(jsonWithInvalidStatus);

        expect(result.status, TenantStatus.active);
      });

      test('should parse emergency contact when present', () {
        final result = TenantModel.fromJson(testJson);

        expect(result.emergencyContact, isNotNull);
        expect(result.emergencyContact!.name, 'Jane Doe');
        expect(result.emergencyContact!.phone, '0987654321');
        expect(result.emergencyContact!.relationship, 'Spouse');
      });

      test('should use current time when dates are missing', () {
        final jsonWithoutDates = {...testJson};
        jsonWithoutDates.remove('created_at');
        jsonWithoutDates.remove('updated_at');

        final beforeParse = DateTime.now();
        final result = TenantModel.fromJson(jsonWithoutDates);
        final afterParse = DateTime.now();

        expect(result.createdAt.isAfter(beforeParse.subtract(const Duration(seconds: 1))), true);
        expect(result.createdAt.isBefore(afterParse.add(const Duration(seconds: 1))), true);
      });
    });

    group('toJson', () {
      test('should return a valid JSON map', () {
        final model = TenantModel.fromJson(testJson);
        final result = model.toJson();

        expect(result['id'], model.id);
        expect(result['first_name'], model.firstName);
        expect(result['last_name'], model.lastName);
        expect(result['email'], model.email);
        expect(result['phone'], model.phone);
        expect(result['date_of_birth'], model.dateOfBirth);
        expect(result['status'], model.status.name);
        expect(result['notes'], model.notes);
        expect(result['profile_image_url'], model.profileImageUrl);
        expect(result['created_at'], isA<String>());
        expect(result['updated_at'], isA<String>());
      });

      test('should omit null optional fields', () {
        final model = TenantModel(
          id: '1',
          firstName: 'John',
          lastName: 'Doe',
          email: 'john@example.com',
          phone: '1234567890',
          status: TenantStatus.active,
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
        );

        final result = model.toJson();

        expect(result.containsKey('date_of_birth'), false);
        expect(result.containsKey('emergency_contact'), false);
        expect(result.containsKey('current_unit_id'), false);
        expect(result.containsKey('current_lease_id'), false);
        expect(result.containsKey('notes'), false);
        expect(result.containsKey('profile_image_url'), false);
      });

      test('should include emergency contact in JSON when present', () {
        final model = TenantModel.fromJson(testJson);
        final result = model.toJson();

        expect(result['emergency_contact'], isA<Map<String, dynamic>>());
        expect(result['emergency_contact']['name'], 'Jane Doe');
        expect(result['emergency_contact']['phone'], '0987654321');
        expect(result['emergency_contact']['relationship'], 'Spouse');
      });

      test('should format dates as ISO 8601 strings', () {
        final model = TenantModel.fromJson(testJson);
        final result = model.toJson();

        expect(result['created_at'], contains('T'));
        expect(result['updated_at'], contains('T'));
        expect(() => DateTime.parse(result['created_at']), returnsNormally);
        expect(() => DateTime.parse(result['updated_at']), returnsNormally);
      });
    });

    group('toCreateJson', () {
      test('should remove id and timestamp fields', () {
        final model = TenantModel.fromJson(testJson);
        final result = model.toCreateJson();

        expect(result.containsKey('id'), false);
        expect(result.containsKey('created_at'), false);
        expect(result.containsKey('updated_at'), false);
        expect(result['first_name'], model.firstName);
        expect(result['last_name'], model.lastName);
        expect(result['email'], model.email);
      });
    });

    group('fromEntity', () {
      test('should convert Tenant entity to TenantModel', () {
        final entity = createTestTenant();
        final model = TenantModel.fromEntity(entity);

        expect(model.id, entity.id);
        expect(model.firstName, entity.firstName);
        expect(model.lastName, entity.lastName);
        expect(model.email, entity.email);
        expect(model.phone, entity.phone);
        expect(model.status, entity.status);
      });
    });

    group('toEntity', () {
      test('should convert TenantModel to Tenant entity', () {
        final model = TenantModel.fromJson(testJson);
        final entity = model.toEntity();

        expect(entity, isA<Tenant>());
        expect(entity.id, model.id);
        expect(entity.firstName, model.firstName);
        expect(entity.lastName, model.lastName);
      });
    });

    group('JSON round-trip', () {
      test('should maintain data integrity through JSON serialization', () {
        final original = TenantModel.fromJson(testJson);
        final json = original.toJson();
        final reconstructed = TenantModel.fromJson(json);

        expect(reconstructed.id, original.id);
        expect(reconstructed.firstName, original.firstName);
        expect(reconstructed.lastName, original.lastName);
        expect(reconstructed.email, original.email);
        expect(reconstructed.phone, original.phone);
        expect(reconstructed.status, original.status);
        expect(reconstructed.emergencyContact?.name, original.emergencyContact?.name);
      });
    });
  });

  group('TenantStatsModel', () {
    test('should create from JSON correctly', () {
      final json = {
        'total_tenants': 100,
        'active_tenants': 75,
        'pending_tenants': 15,
        'inactive_tenants': 10,
      };

      final stats = TenantStatsModel.fromJson(json);

      expect(stats.totalTenants, 100);
      expect(stats.activeTenants, 75);
      expect(stats.pendingTenants, 15);
      expect(stats.inactiveTenants, 10);
    });

    test('should use defaults for missing fields', () {
      final stats = TenantStatsModel.fromJson({});

      expect(stats.totalTenants, 0);
      expect(stats.activeTenants, 0);
      expect(stats.pendingTenants, 0);
      expect(stats.inactiveTenants, 0);
    });

    test('should calculate stats from tenant list', () {
      final tenants = [
        createTestTenant(status: TenantStatus.active),
        createTestTenant(status: TenantStatus.active),
        createTestTenant(status: TenantStatus.active),
        createTestTenant(status: TenantStatus.pending),
        createTestTenant(status: TenantStatus.pending),
        createTestTenant(status: TenantStatus.inactive),
      ];

      final stats = TenantStatsModel.fromTenants(tenants);

      expect(stats.totalTenants, 6);
      expect(stats.activeTenants, 3);
      expect(stats.pendingTenants, 2);
      expect(stats.inactiveTenants, 1);
    });

    test('should return zero stats for empty tenant list', () {
      final stats = TenantStatsModel.fromTenants([]);

      expect(stats.totalTenants, 0);
      expect(stats.activeTenants, 0);
      expect(stats.pendingTenants, 0);
      expect(stats.inactiveTenants, 0);
    });
  });
}
