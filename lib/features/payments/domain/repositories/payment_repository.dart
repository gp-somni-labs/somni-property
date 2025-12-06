import 'package:dartz/dartz.dart';
import 'package:somni_property/core/error/failures.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';

/// Payment repository interface defining data operations
abstract class PaymentRepository {
  /// Get all payments with optional filters
  Future<Either<Failure, List<Payment>>> getPayments({
    String? leaseId,
    String? tenantId,
    String? unitId,
    PaymentStatus? status,
    PaymentType? type,
    DateTime? fromDate,
    DateTime? toDate,
  });

  /// Get a single payment by ID
  Future<Either<Failure, Payment>> getPayment(String id);

  /// Get payments by status
  Future<Either<Failure, List<Payment>>> getPaymentsByStatus(PaymentStatus status);

  /// Get overdue payments
  Future<Either<Failure, List<Payment>>> getOverduePayments();

  /// Get payments due within specified days
  Future<Either<Failure, List<Payment>>> getUpcomingPayments(int withinDays);

  /// Get payments for a specific lease
  Future<Either<Failure, List<Payment>>> getPaymentsForLease(String leaseId);

  /// Get payments for a specific tenant
  Future<Either<Failure, List<Payment>>> getPaymentsForTenant(String tenantId);

  /// Get payment statistics
  Future<Either<Failure, PaymentStats>> getPaymentStats({
    DateTime? fromDate,
    DateTime? toDate,
  });

  /// Create a new payment
  Future<Either<Failure, Payment>> createPayment(Payment payment);

  /// Update an existing payment
  Future<Either<Failure, Payment>> updatePayment(Payment payment);

  /// Record a payment (mark as paid)
  Future<Either<Failure, Payment>> recordPayment(
    String paymentId,
    DateTime paidDate,
    PaymentMethod method,
    String? transactionId,
  );

  /// Apply late fee to a payment
  Future<Either<Failure, Payment>> applyLateFee(
    String paymentId,
    double lateFeeAmount,
  );

  /// Cancel a payment
  Future<Either<Failure, Payment>> cancelPayment(String paymentId, String reason);

  /// Refund a payment
  Future<Either<Failure, Payment>> refundPayment(String paymentId, String reason);

  /// Delete a payment
  Future<Either<Failure, void>> deletePayment(String id);

  /// Generate monthly rent payments for all active leases
  Future<Either<Failure, List<Payment>>> generateMonthlyPayments(
    int month,
    int year,
  );

  /// Create Stripe payment intent
  Future<Either<Failure, Map<String, dynamic>>> createStripePaymentIntent(
    String paymentId,
    double amount,
    String currency,
  );

  /// Process Stripe payment
  Future<Either<Failure, Payment>> processStripePayment(
    String paymentId,
    String paymentIntentId,
  );

  /// Get payment receipt
  Future<Either<Failure, String>> getPaymentReceipt(String paymentId);
}

/// Payment statistics model
class PaymentStats {
  final int totalPayments;
  final int pendingPayments;
  final int paidPayments;
  final int overduePayments;
  final double totalAmountDue;
  final double totalAmountPaid;
  final double totalOverdue;
  final double collectionRate;

  const PaymentStats({
    required this.totalPayments,
    required this.pendingPayments,
    required this.paidPayments,
    required this.overduePayments,
    required this.totalAmountDue,
    required this.totalAmountPaid,
    required this.totalOverdue,
    required this.collectionRate,
  });

  factory PaymentStats.empty() => const PaymentStats(
        totalPayments: 0,
        pendingPayments: 0,
        paidPayments: 0,
        overduePayments: 0,
        totalAmountDue: 0,
        totalAmountPaid: 0,
        totalOverdue: 0,
        collectionRate: 0,
      );

  factory PaymentStats.fromPayments(List<Payment> payments) {
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
          // Partial payments counted as pending
          break;
        case PaymentStatus.overdue:
          overdue++;
          overdueAmount += payment.totalAmount;
          break;
        default:
          break;
      }
    }

    final collectionRate =
        payments.isEmpty ? 0.0 : (paid / payments.length) * 100;

    return PaymentStats(
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
}
