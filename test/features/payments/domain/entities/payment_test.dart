import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';

void main() {
  group('Payment Entity', () {
    late Payment testPayment;

    setUp(() {
      testPayment = Payment(
        id: '1',
        leaseId: 'lease-1',
        tenantId: 'tenant-1',
        unitId: 'unit-1',
        amount: 1500.00,
        dueDate: DateTime(2025, 12, 1),
        status: PaymentStatus.pending,
        type: PaymentType.rent,
        createdAt: DateTime(2025, 11, 1),
        updatedAt: DateTime(2025, 11, 1),
      );
    });

    test('should calculate correct totalAmount without late fee', () {
      expect(testPayment.totalAmount, 1500.00);
    });

    test('should calculate correct totalAmount with late fee', () {
      final paymentWithFee = testPayment.copyWith(lateFee: 50.00);
      expect(paymentWithFee.totalAmount, 1550.00);
    });

    test('should correctly identify overdue payments', () {
      final overduePayment = testPayment.copyWith(
        dueDate: DateTime.now().subtract(const Duration(days: 5)),
      );
      expect(overduePayment.isOverdue, true);
    });

    test('should correctly identify non-overdue payments', () {
      final futurePayment = testPayment.copyWith(
        dueDate: DateTime.now().add(const Duration(days: 5)),
      );
      expect(futurePayment.isOverdue, false);
    });

    test('should calculate correct days overdue', () {
      final now = DateTime.now();
      final overduePayment = testPayment.copyWith(
        dueDate: now.subtract(const Duration(days: 10)),
      );
      expect(overduePayment.daysOverdue, 10);
    });

    test('should return negative days overdue for future payments', () {
      final now = DateTime.now();
      final futurePayment = testPayment.copyWith(
        dueDate: now.add(const Duration(days: 5)),
      );
      expect(futurePayment.daysOverdue < 0, true);
    });

    test('should correctly identify if late fee is applied', () {
      expect(testPayment.hasLateFee, false);

      final paymentWithFee = testPayment.copyWith(lateFee: 50.00);
      expect(paymentWithFee.hasLateFee, true);
    });

    test('should format amount correctly', () {
      expect(testPayment.formattedAmount, '\$1500.00');
    });

    test('should format total amount correctly', () {
      final paymentWithFee = testPayment.copyWith(lateFee: 75.50);
      expect(paymentWithFee.formattedTotalAmount, '\$1575.50');
    });

    test('should format due date correctly', () {
      final payment = testPayment.copyWith(dueDate: DateTime(2025, 12, 15));
      expect(payment.formattedDueDate, '12/15/2025');
    });

    test('should format paid date correctly', () {
      final payment = testPayment.copyWith(paidDate: DateTime(2025, 12, 10));
      expect(payment.formattedPaidDate, '12/10/2025');
    });

    test('should return null for formatted paid date when not paid', () {
      expect(testPayment.formattedPaidDate, null);
    });

    test('should correctly copy with new values', () {
      final updatedPayment = testPayment.copyWith(
        amount: 2000.00,
        status: PaymentStatus.paid,
        paidDate: DateTime(2025, 12, 10),
      );

      expect(updatedPayment.amount, 2000.00);
      expect(updatedPayment.status, PaymentStatus.paid);
      expect(updatedPayment.paidDate, DateTime(2025, 12, 10));
      expect(updatedPayment.id, testPayment.id);
      expect(updatedPayment.leaseId, testPayment.leaseId);
    });

    test('should correctly include Stripe fields', () {
      final stripePayment = testPayment.copyWith(
        stripePaymentIntentId: 'pi_test_123',
        last4: '4242',
        receiptUrl: 'https://stripe.com/receipt/123',
        method: PaymentMethod.creditCard,
      );

      expect(stripePayment.stripePaymentIntentId, 'pi_test_123');
      expect(stripePayment.last4, '4242');
      expect(stripePayment.receiptUrl, 'https://stripe.com/receipt/123');
      expect(stripePayment.method, PaymentMethod.creditCard);
    });

    test('should correctly handle failure reason', () {
      final failedPayment = testPayment.copyWith(
        status: PaymentStatus.cancelled,
        failureReason: 'Card declined',
      );

      expect(failedPayment.failureReason, 'Card declined');
    });
  });

  group('PaymentStatus Enum', () {
    test('should have correct display names', () {
      expect(PaymentStatus.pending.displayName, 'Pending');
      expect(PaymentStatus.paid.displayName, 'Paid');
      expect(PaymentStatus.partial.displayName, 'Partial');
      expect(PaymentStatus.overdue.displayName, 'Overdue');
      expect(PaymentStatus.cancelled.displayName, 'Cancelled');
      expect(PaymentStatus.refunded.displayName, 'Refunded');
    });

    test('should parse from string correctly', () {
      expect(PaymentStatus.fromString('pending'), PaymentStatus.pending);
      expect(PaymentStatus.fromString('paid'), PaymentStatus.paid);
      expect(PaymentStatus.fromString('PAID'), PaymentStatus.paid);
      expect(PaymentStatus.fromString('invalid'), PaymentStatus.pending);
    });
  });

  group('PaymentType Enum', () {
    test('should have correct display names', () {
      expect(PaymentType.rent.displayName, 'Rent');
      expect(PaymentType.deposit.displayName, 'Deposit');
      expect(PaymentType.lateFee.displayName, 'Late Fee');
      expect(PaymentType.utility.displayName, 'Utility');
      expect(PaymentType.maintenance.displayName, 'Maintenance');
      expect(PaymentType.other.displayName, 'Other');
    });

    test('should parse from string correctly', () {
      expect(PaymentType.fromString('rent'), PaymentType.rent);
      expect(PaymentType.fromString('deposit'), PaymentType.deposit);
      expect(PaymentType.fromString('RENT'), PaymentType.rent);
      expect(PaymentType.fromString('invalid'), PaymentType.rent);
    });
  });

  group('PaymentMethod Enum', () {
    test('should have correct display names', () {
      expect(PaymentMethod.cash.displayName, 'Cash');
      expect(PaymentMethod.check.displayName, 'Check');
      expect(PaymentMethod.creditCard.displayName, 'Credit Card');
      expect(PaymentMethod.debitCard.displayName, 'Debit Card');
      expect(PaymentMethod.bankTransfer.displayName, 'Bank Transfer');
      expect(PaymentMethod.online.displayName, 'Online Payment');
      expect(PaymentMethod.other.displayName, 'Other');
    });

    test('should parse from string correctly', () {
      expect(PaymentMethod.fromString('cash'), PaymentMethod.cash);
      expect(PaymentMethod.fromString('credit_card'), PaymentMethod.creditCard);
      expect(PaymentMethod.fromString('creditcard'), PaymentMethod.creditCard);
      expect(PaymentMethod.fromString('invalid'), PaymentMethod.other);
    });
  });
}
