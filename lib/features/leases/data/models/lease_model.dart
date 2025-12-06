import 'package:somni_property/features/leases/domain/entities/lease.dart';

/// Lease model for JSON serialization
class LeaseModel extends Lease {
  const LeaseModel({
    required super.id,
    required super.propertyId,
    required super.unitId,
    required super.tenantId,
    required super.startDate,
    required super.endDate,
    required super.monthlyRent,
    required super.securityDeposit,
    required super.status,
    super.type,
    required super.termMonths,
    super.moveInDate,
    super.moveOutDate,
    super.renewalStatus,
    super.autoRenew,
    super.terminationReason,
    super.terms,
    super.specialConditions,
    super.notes,
    super.attachmentUrls,
    super.propertyName,
    super.unitNumber,
    super.tenantName,
    required super.createdAt,
    required super.updatedAt,
  });

  factory LeaseModel.fromJson(Map<String, dynamic> json) {
    return LeaseModel(
      id: json['id']?.toString() ?? '',
      propertyId: json['property_id']?.toString() ?? '',
      unitId: json['unit_id']?.toString() ?? '',
      tenantId: json['tenant_id']?.toString() ?? '',
      startDate: DateTime.parse(json['start_date'] as String),
      endDate: DateTime.parse(json['end_date'] as String),
      monthlyRent: (json['monthly_rent'] as num).toDouble(),
      securityDeposit: (json['security_deposit'] as num?)?.toDouble() ?? 0.0,
      status: LeaseStatus.values.firstWhere(
        (s) => s.name == json['status'],
        orElse: () => LeaseStatus.active,
      ),
      type: json['type'] != null
          ? LeaseType.values.firstWhere(
              (t) => t.name == json['type'],
              orElse: () => LeaseType.fixed,
            )
          : LeaseType.fixed,
      termMonths: json['term_months'] as int? ?? 12,
      moveInDate: json['move_in_date'] != null
          ? DateTime.parse(json['move_in_date'] as String)
          : null,
      moveOutDate: json['move_out_date'] != null
          ? DateTime.parse(json['move_out_date'] as String)
          : null,
      renewalStatus: json['renewal_status'] as String?,
      autoRenew: json['auto_renew'] as bool? ?? false,
      terminationReason: json['termination_reason'] as String?,
      terms: json['terms'] as String?,
      specialConditions: json['special_conditions'] != null
          ? List<String>.from(json['special_conditions'] as List)
          : null,
      notes: json['notes'] as String?,
      attachmentUrls: json['attachment_urls'] != null
          ? List<String>.from(json['attachment_urls'] as List)
          : null,
      propertyName: json['property_name'] as String?,
      unitNumber: json['unit_number'] as String?,
      tenantName: json['tenant_name'] as String?,
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
      'property_id': propertyId,
      'unit_id': unitId,
      'tenant_id': tenantId,
      'start_date': startDate.toIso8601String(),
      'end_date': endDate.toIso8601String(),
      'monthly_rent': monthlyRent,
      'security_deposit': securityDeposit,
      'status': status.name,
      'type': type.name,
      'term_months': termMonths,
      if (moveInDate != null) 'move_in_date': moveInDate!.toIso8601String(),
      if (moveOutDate != null) 'move_out_date': moveOutDate!.toIso8601String(),
      if (renewalStatus != null) 'renewal_status': renewalStatus,
      'auto_renew': autoRenew,
      if (terminationReason != null) 'termination_reason': terminationReason,
      if (terms != null) 'terms': terms,
      if (specialConditions != null) 'special_conditions': specialConditions,
      if (notes != null) 'notes': notes,
      if (attachmentUrls != null) 'attachment_urls': attachmentUrls,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  /// For creating a new lease (no ID yet)
  Map<String, dynamic> toCreateJson() {
    final json = toJson();
    json.remove('id');
    json.remove('created_at');
    json.remove('updated_at');
    json.remove('unit_number');
    json.remove('tenant_name');
    return json;
  }

  /// Convert entity to model
  factory LeaseModel.fromEntity(Lease lease) {
    return LeaseModel(
      id: lease.id,
      propertyId: lease.propertyId,
      unitId: lease.unitId,
      tenantId: lease.tenantId,
      startDate: lease.startDate,
      endDate: lease.endDate,
      monthlyRent: lease.monthlyRent,
      securityDeposit: lease.securityDeposit,
      status: lease.status,
      type: lease.type,
      termMonths: lease.termMonths,
      moveInDate: lease.moveInDate,
      moveOutDate: lease.moveOutDate,
      renewalStatus: lease.renewalStatus,
      autoRenew: lease.autoRenew,
      terminationReason: lease.terminationReason,
      terms: lease.terms,
      specialConditions: lease.specialConditions,
      notes: lease.notes,
      attachmentUrls: lease.attachmentUrls,
      propertyName: lease.propertyName,
      unitNumber: lease.unitNumber,
      tenantName: lease.tenantName,
      createdAt: lease.createdAt,
      updatedAt: lease.updatedAt,
    );
  }

  /// Convert to domain entity
  Lease toEntity() => this;
}

/// Lease statistics model
class LeaseStatsModel {
  final int totalLeases;
  final int activeLeases;
  final int expiringLeases;
  final int pendingLeases;
  final double totalMonthlyRevenue;

  const LeaseStatsModel({
    required this.totalLeases,
    required this.activeLeases,
    required this.expiringLeases,
    required this.pendingLeases,
    required this.totalMonthlyRevenue,
  });

  factory LeaseStatsModel.fromJson(Map<String, dynamic> json) {
    return LeaseStatsModel(
      totalLeases: json['total_leases'] as int? ?? 0,
      activeLeases: json['active_leases'] as int? ?? 0,
      expiringLeases: json['expiring_leases'] as int? ?? 0,
      pendingLeases: json['pending_leases'] as int? ?? 0,
      totalMonthlyRevenue:
          (json['total_monthly_revenue'] as num?)?.toDouble() ?? 0.0,
    );
  }

  factory LeaseStatsModel.fromLeases(List<Lease> leases) {
    final activeLeases =
        leases.where((l) => l.status == LeaseStatus.active).toList();
    return LeaseStatsModel(
      totalLeases: leases.length,
      activeLeases: activeLeases.length,
      expiringLeases: activeLeases.where((l) => l.isExpiringSoon).length,
      pendingLeases:
          leases.where((l) => l.status == LeaseStatus.pending).length,
      totalMonthlyRevenue:
          activeLeases.fold(0.0, (sum, l) => sum + l.monthlyRent),
    );
  }
}
