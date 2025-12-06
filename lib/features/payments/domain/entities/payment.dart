import 'package:equatable/equatable.dart';

/// Payment entity representing a rent payment or transaction
class Payment extends Equatable {
  final String id;
  final String leaseId;
  final String tenantId;
  final String unitId;
  final double amount;
  final DateTime dueDate;
  final DateTime? paidDate;
  final PaymentStatus status;
  final PaymentType type;
  final PaymentMethod? method;
  final String? transactionId;
  final String? notes;
  final double? lateFee;
  final DateTime createdAt;
  final DateTime updatedAt;

  // Stripe-specific fields
  final String? stripePaymentIntentId;
  final String? last4; // Card last 4 digits
  final String? receiptUrl;
  final String? failureReason;

  // Joined data from related entities
  final String? tenantName;
  final String? unitNumber;

  const Payment({
    required this.id,
    required this.leaseId,
    required this.tenantId,
    required this.unitId,
    required this.amount,
    required this.dueDate,
    this.paidDate,
    required this.status,
    required this.type,
    this.method,
    this.transactionId,
    this.notes,
    this.lateFee,
    required this.createdAt,
    required this.updatedAt,
    this.stripePaymentIntentId,
    this.last4,
    this.receiptUrl,
    this.failureReason,
    this.tenantName,
    this.unitNumber,
  });

  /// Check if payment is overdue
  bool get isOverdue =>
      status == PaymentStatus.pending &&
      DateTime.now().isAfter(dueDate);

  /// Get days overdue (negative if not yet due)
  int get daysOverdue =>
      DateTime.now().difference(dueDate).inDays;

  /// Get total amount including late fee
  double get totalAmount => amount + (lateFee ?? 0);

  /// Check if payment has late fee applied
  bool get hasLateFee => lateFee != null && lateFee! > 0;

  /// Get formatted amount
  String get formattedAmount => '\$${amount.toStringAsFixed(2)}';

  /// Get formatted total amount
  String get formattedTotalAmount => '\$${totalAmount.toStringAsFixed(2)}';

  /// Get formatted due date
  String get formattedDueDate =>
      '${dueDate.month}/${dueDate.day}/${dueDate.year}';

  /// Get formatted paid date
  String? get formattedPaidDate => paidDate != null
      ? '${paidDate!.month}/${paidDate!.day}/${paidDate!.year}'
      : null;

  /// Copy with new values
  Payment copyWith({
    String? id,
    String? leaseId,
    String? tenantId,
    String? unitId,
    double? amount,
    DateTime? dueDate,
    DateTime? paidDate,
    PaymentStatus? status,
    PaymentType? type,
    PaymentMethod? method,
    String? transactionId,
    String? notes,
    double? lateFee,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? stripePaymentIntentId,
    String? last4,
    String? receiptUrl,
    String? failureReason,
    String? tenantName,
    String? unitNumber,
  }) {
    return Payment(
      id: id ?? this.id,
      leaseId: leaseId ?? this.leaseId,
      tenantId: tenantId ?? this.tenantId,
      unitId: unitId ?? this.unitId,
      amount: amount ?? this.amount,
      dueDate: dueDate ?? this.dueDate,
      paidDate: paidDate ?? this.paidDate,
      status: status ?? this.status,
      type: type ?? this.type,
      method: method ?? this.method,
      transactionId: transactionId ?? this.transactionId,
      notes: notes ?? this.notes,
      lateFee: lateFee ?? this.lateFee,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      stripePaymentIntentId: stripePaymentIntentId ?? this.stripePaymentIntentId,
      last4: last4 ?? this.last4,
      receiptUrl: receiptUrl ?? this.receiptUrl,
      failureReason: failureReason ?? this.failureReason,
      tenantName: tenantName ?? this.tenantName,
      unitNumber: unitNumber ?? this.unitNumber,
    );
  }

  @override
  List<Object?> get props => [
        id,
        leaseId,
        tenantId,
        unitId,
        amount,
        dueDate,
        paidDate,
        status,
        type,
        method,
        transactionId,
        notes,
        lateFee,
        createdAt,
        updatedAt,
      ];
}

/// Payment status enumeration
enum PaymentStatus {
  pending,
  paid,
  partial,
  overdue,
  cancelled,
  refunded;

  String get displayName {
    switch (this) {
      case PaymentStatus.pending:
        return 'Pending';
      case PaymentStatus.paid:
        return 'Paid';
      case PaymentStatus.partial:
        return 'Partial';
      case PaymentStatus.overdue:
        return 'Overdue';
      case PaymentStatus.cancelled:
        return 'Cancelled';
      case PaymentStatus.refunded:
        return 'Refunded';
    }
  }

  static PaymentStatus fromString(String value) {
    return PaymentStatus.values.firstWhere(
      (status) => status.name.toLowerCase() == value.toLowerCase(),
      orElse: () => PaymentStatus.pending,
    );
  }
}

/// Payment type enumeration
enum PaymentType {
  rent,
  deposit,
  lateFee,
  utility,
  maintenance,
  other;

  String get displayName {
    switch (this) {
      case PaymentType.rent:
        return 'Rent';
      case PaymentType.deposit:
        return 'Deposit';
      case PaymentType.lateFee:
        return 'Late Fee';
      case PaymentType.utility:
        return 'Utility';
      case PaymentType.maintenance:
        return 'Maintenance';
      case PaymentType.other:
        return 'Other';
    }
  }

  static PaymentType fromString(String value) {
    return PaymentType.values.firstWhere(
      (type) => type.name.toLowerCase() == value.toLowerCase(),
      orElse: () => PaymentType.rent,
    );
  }
}

/// Payment method enumeration
enum PaymentMethod {
  cash,
  check,
  creditCard,
  debitCard,
  bankTransfer,
  online,
  other;

  String get displayName {
    switch (this) {
      case PaymentMethod.cash:
        return 'Cash';
      case PaymentMethod.check:
        return 'Check';
      case PaymentMethod.creditCard:
        return 'Credit Card';
      case PaymentMethod.debitCard:
        return 'Debit Card';
      case PaymentMethod.bankTransfer:
        return 'Bank Transfer';
      case PaymentMethod.online:
        return 'Online Payment';
      case PaymentMethod.other:
        return 'Other';
    }
  }

  static PaymentMethod fromString(String value) {
    switch (value.toLowerCase().replaceAll('_', '')) {
      case 'cash':
        return PaymentMethod.cash;
      case 'check':
        return PaymentMethod.check;
      case 'creditcard':
        return PaymentMethod.creditCard;
      case 'debitcard':
        return PaymentMethod.debitCard;
      case 'banktransfer':
        return PaymentMethod.bankTransfer;
      case 'online':
        return PaymentMethod.online;
      default:
        return PaymentMethod.other;
    }
  }
}
