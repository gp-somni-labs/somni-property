import 'package:somni_property/features/tenants/domain/entities/tenant.dart';
import 'package:somni_property/features/tenants/data/models/tenant_model.dart';

/// Test fixture for Tenant entity
Tenant createTestTenant({
  String id = 'test-tenant-1',
  String firstName = 'John',
  String lastName = 'Doe',
  String email = 'john.doe@example.com',
  String phone = '1234567890',
  String? dateOfBirth = '1990-01-01',
  EmergencyContact? emergencyContact,
  String? currentUnitId = 'unit-1',
  String? currentLeaseId = 'lease-1',
  TenantStatus status = TenantStatus.active,
  String? notes = 'Test notes',
  String? profileImageUrl,
  DateTime? createdAt,
  DateTime? updatedAt,
}) {
  final now = DateTime.now();
  return Tenant(
    id: id,
    firstName: firstName,
    lastName: lastName,
    email: email,
    phone: phone,
    dateOfBirth: dateOfBirth,
    emergencyContact: emergencyContact ?? createTestEmergencyContact(),
    currentUnitId: currentUnitId,
    currentLeaseId: currentLeaseId,
    status: status,
    notes: notes,
    profileImageUrl: profileImageUrl,
    createdAt: createdAt ?? now,
    updatedAt: updatedAt ?? now,
  );
}

/// Test fixture for EmergencyContact
EmergencyContact createTestEmergencyContact({
  String name = 'Jane Doe',
  String phone = '0987654321',
  String relationship = 'Spouse',
}) {
  return EmergencyContact(
    name: name,
    phone: phone,
    relationship: relationship,
  );
}

/// Sample JSON response for tenant
Map<String, dynamic> tenantJsonFixture({
  String id = 'test-tenant-1',
  String firstName = 'John',
  String lastName = 'Doe',
}) {
  return {
    'id': id,
    'first_name': firstName,
    'last_name': lastName,
    'email': 'john.doe@example.com',
    'phone': '1234567890',
    'date_of_birth': '1990-01-01',
    'emergency_contact': {
      'name': 'Jane Doe',
      'phone': '0987654321',
      'relationship': 'Spouse',
    },
    'current_unit_id': 'unit-1',
    'current_lease_id': 'lease-1',
    'status': 'active',
    'notes': 'Test notes',
    'profile_image_url': 'https://example.com/profile.jpg',
    'created_at': '2025-01-01T00:00:00.000Z',
    'updated_at': '2025-01-01T00:00:00.000Z',
  };
}

/// List of test tenants
List<Tenant> createTestTenantsList({int count = 3}) {
  return List.generate(
    count,
    (index) => createTestTenant(
      id: 'tenant-$index',
      firstName: 'Tenant$index',
      lastName: 'Last$index',
      email: 'tenant$index@example.com',
    ),
  );
}
