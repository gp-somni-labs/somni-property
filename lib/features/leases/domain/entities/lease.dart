import 'package:equatable/equatable.dart';

/// Lease entity representing a rental agreement
class Lease extends Equatable {
  final String id;
  final String propertyId;
  final String unitId;
  final String tenantId;
  final DateTime startDate;
  final DateTime endDate;
  final double monthlyRent;
  final double securityDeposit;
  final LeaseStatus status;
  final LeaseType type;
  final int termMonths;
  final DateTime? moveInDate;
  final DateTime? moveOutDate;
  final String? renewalStatus;
  final bool autoRenew;
  final String? terminationReason;
  final String? terms;
  final List<String>? specialConditions;
  final String? notes;
  final List<String>? attachmentUrls;
  final String? propertyName;
  final String? unitNumber;
  final String? tenantName;
  final DateTime createdAt;
  final DateTime updatedAt;

  const Lease({
    required this.id,
    required this.propertyId,
    required this.unitId,
    required this.tenantId,
    required this.startDate,
    required this.endDate,
    required this.monthlyRent,
    required this.securityDeposit,
    required this.status,
    this.type = LeaseType.fixed,
    required this.termMonths,
    this.moveInDate,
    this.moveOutDate,
    this.renewalStatus,
    this.autoRenew = false,
    this.terminationReason,
    this.terms,
    this.specialConditions,
    this.notes,
    this.attachmentUrls,
    this.propertyName,
    this.unitNumber,
    this.tenantName,
    required this.createdAt,
    required this.updatedAt,
  });

  /// Check if lease is active
  bool get isActive => status == LeaseStatus.active;

  /// Check if lease is expiring soon (within 30 days)
  bool get isExpiringSoon {
    final now = DateTime.now();
    final daysUntilExpiry = endDate.difference(now).inDays;
    return status == LeaseStatus.active && daysUntilExpiry <= 30 && daysUntilExpiry > 0;
  }

  /// Check if lease has expired
  bool get hasExpired {
    return DateTime.now().isAfter(endDate);
  }

  /// Get days until lease expires
  int get daysUntilExpiry {
    return endDate.difference(DateTime.now()).inDays;
  }

  /// Get lease duration in months
  int get durationMonths => termMonths;

  /// Get total lease value
  double get totalValue => monthlyRent * termMonths;

  /// Check if tenant has moved in
  bool get hasMoveIn => moveInDate != null;

  /// Check if tenant has moved out
  bool get hasMoveOut => moveOutDate != null;

  /// Check if lease is pending renewal
  bool get isPendingRenewal => renewalStatus == 'pending';

  /// Check if lease can be renewed
  bool get canBeRenewed => isActive && !isPendingRenewal;

  /// Get formatted date range
  String get dateRangeFormatted {
    return '${_formatDate(startDate)} - ${_formatDate(endDate)}';
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year}';
  }

  @override
  List<Object?> get props => [
        id,
        propertyId,
        unitId,
        tenantId,
        startDate,
        endDate,
        monthlyRent,
        securityDeposit,
        status,
        type,
        termMonths,
        moveInDate,
        moveOutDate,
        renewalStatus,
        autoRenew,
        terminationReason,
        terms,
        specialConditions,
        notes,
        attachmentUrls,
        propertyName,
        unitNumber,
        tenantName,
        createdAt,
        updatedAt,
      ];

  Lease copyWith({
    String? id,
    String? propertyId,
    String? unitId,
    String? tenantId,
    DateTime? startDate,
    DateTime? endDate,
    double? monthlyRent,
    double? securityDeposit,
    LeaseStatus? status,
    LeaseType? type,
    int? termMonths,
    DateTime? moveInDate,
    DateTime? moveOutDate,
    String? renewalStatus,
    bool? autoRenew,
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
    return Lease(
      id: id ?? this.id,
      propertyId: propertyId ?? this.propertyId,
      unitId: unitId ?? this.unitId,
      tenantId: tenantId ?? this.tenantId,
      startDate: startDate ?? this.startDate,
      endDate: endDate ?? this.endDate,
      monthlyRent: monthlyRent ?? this.monthlyRent,
      securityDeposit: securityDeposit ?? this.securityDeposit,
      status: status ?? this.status,
      type: type ?? this.type,
      termMonths: termMonths ?? this.termMonths,
      moveInDate: moveInDate ?? this.moveInDate,
      moveOutDate: moveOutDate ?? this.moveOutDate,
      renewalStatus: renewalStatus ?? this.renewalStatus,
      autoRenew: autoRenew ?? this.autoRenew,
      terminationReason: terminationReason ?? this.terminationReason,
      terms: terms ?? this.terms,
      specialConditions: specialConditions ?? this.specialConditions,
      notes: notes ?? this.notes,
      attachmentUrls: attachmentUrls ?? this.attachmentUrls,
      propertyName: propertyName ?? this.propertyName,
      unitNumber: unitNumber ?? this.unitNumber,
      tenantName: tenantName ?? this.tenantName,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

/// Lease status
enum LeaseStatus {
  pending('Pending'),
  active('Active'),
  expiring('Expiring'),
  expired('Expired'),
  terminated('Terminated'),
  renewed('Renewed');

  final String displayName;
  const LeaseStatus(this.displayName);
}

/// Lease type
enum LeaseType {
  fixed('Fixed Term'),
  monthToMonth('Month-to-Month');

  final String displayName;
  const LeaseType(this.displayName);
}
