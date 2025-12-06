import 'package:somni_property/features/tenants/domain/entities/tenant.dart';

/// Tenant model for JSON serialization
class TenantModel extends Tenant {
  const TenantModel({
    required super.id,
    required super.firstName,
    required super.lastName,
    required super.email,
    required super.phone,
    super.dateOfBirth,
    super.emergencyContact,
    super.currentUnitId,
    super.currentLeaseId,
    required super.status,
    super.notes,
    super.profileImageUrl,
    required super.createdAt,
    required super.updatedAt,
  });

  factory TenantModel.fromJson(Map<String, dynamic> json) {
    return TenantModel(
      id: json['id']?.toString() ?? '',
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      email: json['email'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      dateOfBirth: json['date_of_birth'] as String?,
      emergencyContact: json['emergency_contact'] != null
          ? EmergencyContact.fromJson(
              json['emergency_contact'] as Map<String, dynamic>)
          : null,
      currentUnitId: json['current_unit_id']?.toString(),
      currentLeaseId: json['current_lease_id']?.toString(),
      status: TenantStatus.values.firstWhere(
        (s) => s.name == json['status'],
        orElse: () => TenantStatus.active,
      ),
      notes: json['notes'] as String?,
      profileImageUrl: json['profile_image_url'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'first_name': firstName,
      'last_name': lastName,
      'email': email,
      'phone': phone,
      if (dateOfBirth != null) 'date_of_birth': dateOfBirth,
      if (emergencyContact != null)
        'emergency_contact': emergencyContact!.toJson(),
      if (currentUnitId != null) 'current_unit_id': currentUnitId,
      if (currentLeaseId != null) 'current_lease_id': currentLeaseId,
      'status': status.name,
      if (notes != null) 'notes': notes,
      if (profileImageUrl != null) 'profile_image_url': profileImageUrl,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  /// For creating a new tenant (no ID yet)
  Map<String, dynamic> toCreateJson() {
    final json = toJson();
    json.remove('id');
    json.remove('created_at');
    json.remove('updated_at');
    return json;
  }

  /// Convert entity to model
  factory TenantModel.fromEntity(Tenant tenant) {
    return TenantModel(
      id: tenant.id,
      firstName: tenant.firstName,
      lastName: tenant.lastName,
      email: tenant.email,
      phone: tenant.phone,
      dateOfBirth: tenant.dateOfBirth,
      emergencyContact: tenant.emergencyContact,
      currentUnitId: tenant.currentUnitId,
      currentLeaseId: tenant.currentLeaseId,
      status: tenant.status,
      notes: tenant.notes,
      profileImageUrl: tenant.profileImageUrl,
      createdAt: tenant.createdAt,
      updatedAt: tenant.updatedAt,
    );
  }

  /// Convert to domain entity
  Tenant toEntity() => this;
}

/// Tenant statistics model
class TenantStatsModel {
  final int totalTenants;
  final int activeTenants;
  final int pendingTenants;
  final int inactiveTenants;

  const TenantStatsModel({
    required this.totalTenants,
    required this.activeTenants,
    required this.pendingTenants,
    required this.inactiveTenants,
  });

  factory TenantStatsModel.fromJson(Map<String, dynamic> json) {
    return TenantStatsModel(
      totalTenants: json['total_tenants'] as int? ?? 0,
      activeTenants: json['active_tenants'] as int? ?? 0,
      pendingTenants: json['pending_tenants'] as int? ?? 0,
      inactiveTenants: json['inactive_tenants'] as int? ?? 0,
    );
  }

  factory TenantStatsModel.fromTenants(List<Tenant> tenants) {
    return TenantStatsModel(
      totalTenants: tenants.length,
      activeTenants:
          tenants.where((t) => t.status == TenantStatus.active).length,
      pendingTenants:
          tenants.where((t) => t.status == TenantStatus.pending).length,
      inactiveTenants:
          tenants.where((t) => t.status == TenantStatus.inactive).length,
    );
  }
}
