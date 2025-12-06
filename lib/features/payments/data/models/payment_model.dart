import 'package:somni_property/features/payments/domain/entities/payment.dart';

/// Payment model for JSON serialization
class PaymentModel extends Payment {
  const PaymentModel({
    required super.id,
    required super.leaseId,
    required super.tenantId,
    required super.unitId,
    required super.amount,
    required super.dueDate,
    super.paidDate,
    required super.status,
    required super.type,
    super.method,
    super.transactionId,
    super.notes,
    super.lateFee,
    required super.createdAt,
    required super.updatedAt,
    super.stripePaymentIntentId,
    super.last4,
    super.receiptUrl,
    super.failureReason,
    super.tenantName,
    super.unitNumber,
  });

  /// Create model from JSON
  factory PaymentModel.fromJson(Map<String, dynamic> json) {
    return PaymentModel(
      id: json['id']?.toString() ?? '',
      leaseId: json['lease_id']?.toString() ?? json['leaseId']?.toString() ?? '',
      tenantId: json['tenant_id']?.toString() ?? json['tenantId']?.toString() ?? '',
      unitId: json['unit_id']?.toString() ?? json['unitId']?.toString() ?? '',
      amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
      dueDate: json['due_date'] != null
          ? DateTime.parse(json['due_date'])
          : json['dueDate'] != null
              ? DateTime.parse(json['dueDate'])
              : DateTime.now(),
      paidDate: json['paid_date'] != null
          ? DateTime.parse(json['paid_date'])
          : json['paidDate'] != null
              ? DateTime.parse(json['paidDate'])
              : null,
      status: PaymentStatus.fromString(
        json['status']?.toString() ?? 'pending',
      ),
      type: PaymentType.fromString(
        json['type']?.toString() ?? json['payment_type']?.toString() ?? 'rent',
      ),
      method: json['method'] != null || json['payment_method'] != null
          ? PaymentMethod.fromString(
              json['method']?.toString() ?? json['payment_method']?.toString() ?? '',
            )
          : null,
      transactionId: json['transaction_id']?.toString() ?? json['transactionId']?.toString(),
      notes: json['notes']?.toString(),
      lateFee: (json['late_fee'] as num?)?.toDouble() ?? (json['lateFee'] as num?)?.toDouble(),
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : json['createdAt'] != null
              ? DateTime.parse(json['createdAt'])
              : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : json['updatedAt'] != null
              ? DateTime.parse(json['updatedAt'])
              : DateTime.now(),
      stripePaymentIntentId: json['stripe_payment_intent_id']?.toString() ??
          json['stripePaymentIntentId']?.toString(),
      last4: json['last4']?.toString(),
      receiptUrl: json['receipt_url']?.toString() ?? json['receiptUrl']?.toString(),
      failureReason: json['failure_reason']?.toString() ?? json['failureReason']?.toString(),
      tenantName: json['tenant_name']?.toString() ?? json['tenantName']?.toString(),
      unitNumber: json['unit_number']?.toString() ?? json['unitNumber']?.toString(),
    );
  }

  /// Convert model to JSON for API requests
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'lease_id': leaseId,
      'tenant_id': tenantId,
      'unit_id': unitId,
      'amount': amount,
      'due_date': dueDate.toIso8601String(),
      if (paidDate != null) 'paid_date': paidDate!.toIso8601String(),
      'status': status.name,
      'type': type.name,
      if (method != null) 'method': method!.name,
      if (transactionId != null) 'transaction_id': transactionId,
      if (notes != null) 'notes': notes,
      if (lateFee != null) 'late_fee': lateFee,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      if (stripePaymentIntentId != null) 'stripe_payment_intent_id': stripePaymentIntentId,
      if (last4 != null) 'last4': last4,
      if (receiptUrl != null) 'receipt_url': receiptUrl,
      if (failureReason != null) 'failure_reason': failureReason,
    };
  }

  /// Create model from entity
  factory PaymentModel.fromEntity(Payment payment) {
    return PaymentModel(
      id: payment.id,
      leaseId: payment.leaseId,
      tenantId: payment.tenantId,
      unitId: payment.unitId,
      amount: payment.amount,
      dueDate: payment.dueDate,
      paidDate: payment.paidDate,
      status: payment.status,
      type: payment.type,
      method: payment.method,
      transactionId: payment.transactionId,
      notes: payment.notes,
      lateFee: payment.lateFee,
      createdAt: payment.createdAt,
      updatedAt: payment.updatedAt,
      stripePaymentIntentId: payment.stripePaymentIntentId,
      last4: payment.last4,
      receiptUrl: payment.receiptUrl,
      failureReason: payment.failureReason,
      tenantName: payment.tenantName,
      unitNumber: payment.unitNumber,
    );
  }

  /// Convert to entity
  Payment toEntity() {
    return Payment(
      id: id,
      leaseId: leaseId,
      tenantId: tenantId,
      unitId: unitId,
      amount: amount,
      dueDate: dueDate,
      paidDate: paidDate,
      status: status,
      type: type,
      method: method,
      transactionId: transactionId,
      notes: notes,
      lateFee: lateFee,
      createdAt: createdAt,
      updatedAt: updatedAt,
      stripePaymentIntentId: stripePaymentIntentId,
      last4: last4,
      receiptUrl: receiptUrl,
      failureReason: failureReason,
      tenantName: tenantName,
      unitNumber: unitNumber,
    );
  }
}

/// Payment statistics model for state management
class PaymentStatsModel {
  final int totalPayments;
  final int pendingPayments;
  final int paidPayments;
  final int overduePayments;
  final double totalAmountDue;
  final double totalAmountPaid;
  final double totalOverdue;
  final double collectionRate;

  const PaymentStatsModel({
    required this.totalPayments,
    required this.pendingPayments,
    required this.paidPayments,
    required this.overduePayments,
    required this.totalAmountDue,
    required this.totalAmountPaid,
    required this.totalOverdue,
    required this.collectionRate,
  });

  factory PaymentStatsModel.empty() => const PaymentStatsModel(
        totalPayments: 0,
        pendingPayments: 0,
        paidPayments: 0,
        overduePayments: 0,
        totalAmountDue: 0,
        totalAmountPaid: 0,
        totalOverdue: 0,
        collectionRate: 0,
      );

  factory PaymentStatsModel.fromPayments(List<Payment> payments) {
    final now = DateTime.now();
    int pending = 0;
    int paid = 0;
    int overdue = 0;
    double amountDue = 0;
    double amountPaid = 0;
    double overdueAmount = 0;

    for (final payment in payments) {
      switch (payment.status) {
        case PaymentStatus.pending:
          pending++;
          amountDue += payment.totalAmount;
          if (now.isAfter(payment.dueDate)) {
            overdue++;
            overdueAmount += payment.totalAmount;
          }
          break;
        case PaymentStatus.paid:
          paid++;
          amountPaid += payment.totalAmount;
          break;
        case PaymentStatus.partial:
          pending++;
          break;
        case PaymentStatus.overdue:
          overdue++;
          overdueAmount += payment.totalAmount;
          amountDue += payment.totalAmount;
          break;
        default:
          break;
      }
    }

    final collectionRate =
        (amountDue + amountPaid) == 0 ? 0.0 : (amountPaid / (amountDue + amountPaid)) * 100;

    return PaymentStatsModel(
      totalPayments: payments.length,
      pendingPayments: pending,
      paidPayments: paid,
      overduePayments: overdue,
      totalAmountDue: amountDue,
      totalAmountPaid: amountPaid,
      totalOverdue: overdueAmount,
      collectionRate: collectionRate,
    );
  }

  factory PaymentStatsModel.fromJson(Map<String, dynamic> json) {
    return PaymentStatsModel(
      totalPayments: json['total_payments'] as int? ?? 0,
      pendingPayments: json['pending_payments'] as int? ?? 0,
      paidPayments: json['paid_payments'] as int? ?? 0,
      overduePayments: json['overdue_payments'] as int? ?? 0,
      totalAmountDue: (json['total_amount_due'] as num?)?.toDouble() ?? 0,
      totalAmountPaid: (json['total_amount_paid'] as num?)?.toDouble() ?? 0,
      totalOverdue: (json['total_overdue'] as num?)?.toDouble() ?? 0,
      collectionRate: (json['collection_rate'] as num?)?.toDouble() ?? 0,
    );
  }
}
