import 'package:somni_property/features/leases/domain/entities/lease.dart';

/// Test fixture for Lease entity
Lease createTestLease({
  String id = 'test-lease-1',
  String propertyId = 'property-1',
  String unitId = 'unit-1',
  String tenantId = 'tenant-1',
  DateTime? startDate,
  DateTime? endDate,
  double monthlyRent = 1500.0,
  double securityDeposit = 1500.0,
  LeaseStatus status = LeaseStatus.active,
  LeaseType type = LeaseType.fixed,
  int termMonths = 12,
  DateTime? moveInDate,
  DateTime? moveOutDate,
  String? renewalStatus,
  bool autoRenew = false,
  String? terminationReason,
  String? terms,
  List<String>? specialConditions,
  String? notes,
  List<String>? attachmentUrls,
  String? propertyName,
  String? unitNumber,
  String? tenantName,
  DateTime? createdAt,
  DateTime? updatedAt,
}) {
  final now = DateTime.now();
  return Lease(
    id: id,
    propertyId: propertyId,
    unitId: unitId,
    tenantId: tenantId,
    startDate: startDate ?? now,
    endDate: endDate ?? now.add(const Duration(days: 365)),
    monthlyRent: monthlyRent,
    securityDeposit: securityDeposit,
    status: status,
    type: type,
    termMonths: termMonths,
    moveInDate: moveInDate,
    moveOutDate: moveOutDate,
    renewalStatus: renewalStatus,
    autoRenew: autoRenew,
    terminationReason: terminationReason,
    terms: terms,
    specialConditions: specialConditions,
    notes: notes,
    attachmentUrls: attachmentUrls,
    propertyName: propertyName,
    unitNumber: unitNumber,
    tenantName: tenantName,
    createdAt: createdAt ?? now,
    updatedAt: updatedAt ?? now,
  );
}

/// Sample JSON response for lease
Map<String, dynamic> leaseJsonFixture({
  String id = 'test-lease-1',
}) {
  final now = DateTime.now();
  return {
    'id': id,
    'property_id': 'property-1',
    'unit_id': 'unit-1',
    'tenant_id': 'tenant-1',
    'start_date': now.toIso8601String(),
    'end_date': now.add(const Duration(days: 365)).toIso8601String(),
    'monthly_rent': 1500.0,
    'security_deposit': 1500.0,
    'status': 'active',
    'type': 'fixed',
    'term_months': 12,
    'move_in_date': now.toIso8601String(),
    'auto_renew': false,
    'terms': 'Standard lease terms',
    'special_conditions': ['No pets', 'No smoking'],
    'notes': 'Test lease notes',
    'property_name': 'Test Property',
    'unit_number': 'Unit 101',
    'tenant_name': 'John Doe',
    'created_at': now.toIso8601String(),
    'updated_at': now.toIso8601String(),
  };
}

/// List of test leases
List<Lease> createTestLeasesList({int count = 3}) {
  return List.generate(
    count,
    (index) => createTestLease(
      id: 'lease-$index',
      monthlyRent: 1000.0 + (index * 100),
    ),
  );
}
