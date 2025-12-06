import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/features/leases/domain/entities/lease.dart';
import '../../../../fixtures/lease_fixtures.dart';

void main() {
  group('Lease Entity', () {
    late Lease testLease;

    setUp(() {
      testLease = createTestLease(
        startDate: DateTime(2025, 1, 1),
        endDate: DateTime(2025, 12, 31),
        monthlyRent: 2000.0,
        termMonths: 12,
        status: LeaseStatus.active,
      );
    });

    test('should correctly identify active lease', () {
      expect(testLease.isActive, true);

      final inactive = testLease.copyWith(status: LeaseStatus.expired);
      expect(inactive.isActive, false);
    });

    test('should correctly identify expiring lease', () {
      final now = DateTime.now();
      final expiringSoon = createTestLease(
        startDate: now.subtract(const Duration(days: 335)),
        endDate: now.add(const Duration(days: 20)),
        status: LeaseStatus.active,
      );
      expect(expiringSoon.isExpiringSoon, true);

      final notExpiring = createTestLease(
        startDate: now.subtract(const Duration(days: 300)),
        endDate: now.add(const Duration(days: 60)),
        status: LeaseStatus.active,
      );
      expect(notExpiring.isExpiringSoon, false);
    });

    test('should correctly identify expired lease', () {
      final expired = createTestLease(
        endDate: DateTime.now().subtract(const Duration(days: 1)),
      );
      expect(expired.hasExpired, true);

      final notExpired = createTestLease(
        endDate: DateTime.now().add(const Duration(days: 30)),
      );
      expect(notExpired.hasExpired, false);
    });

    test('should calculate days until expiry correctly', () {
      final now = DateTime.now();
      final lease = createTestLease(
        endDate: now.add(const Duration(days: 30)),
      );
      expect(lease.daysUntilExpiry, 30);
    });

    test('should calculate total lease value correctly', () {
      expect(testLease.totalValue, 24000.0); // 2000 * 12
    });

    test('should correctly identify move-in status', () {
      final withMoveIn = testLease.copyWith(
        moveInDate: DateTime(2025, 1, 1),
      );
      expect(withMoveIn.hasMoveIn, true);

      expect(testLease.hasMoveIn, false);
    });

    test('should correctly identify move-out status', () {
      final withMoveOut = testLease.copyWith(
        moveOutDate: DateTime(2025, 12, 31),
      );
      expect(withMoveOut.hasMoveOut, true);

      expect(testLease.hasMoveOut, false);
    });

    test('should correctly identify pending renewal', () {
      final pendingRenewal = testLease.copyWith(renewalStatus: 'pending');
      expect(pendingRenewal.isPendingRenewal, true);

      expect(testLease.isPendingRenewal, false);
    });

    test('should correctly identify if can be renewed', () {
      expect(testLease.canBeRenewed, true);

      final pending = testLease.copyWith(renewalStatus: 'pending');
      expect(pending.canBeRenewed, false);

      final expired = testLease.copyWith(status: LeaseStatus.expired);
      expect(expired.canBeRenewed, false);
    });

    test('should format date range correctly', () {
      expect(testLease.dateRangeFormatted, '1/1/2025 - 12/31/2025');
    });

    test('should return duration in months', () {
      expect(testLease.durationMonths, 12);
    });

    test('should create copy with new values', () {
      final updated = testLease.copyWith(
        monthlyRent: 2500.0,
        status: LeaseStatus.renewed,
        autoRenew: true,
      );

      expect(updated.monthlyRent, 2500.0);
      expect(updated.status, LeaseStatus.renewed);
      expect(updated.autoRenew, true);
      expect(updated.id, testLease.id);
      expect(updated.propertyId, testLease.propertyId);
    });

    test('should support equality comparison', () {
      final lease1 = createTestLease(id: 'lease-1');
      final lease2 = createTestLease(id: 'lease-1');
      final lease3 = createTestLease(id: 'lease-2');

      expect(lease1, equals(lease2));
      expect(lease1, isNot(equals(lease3)));
    });
  });

  group('LeaseStatus Enum', () {
    test('should have correct display names', () {
      expect(LeaseStatus.pending.displayName, 'Pending');
      expect(LeaseStatus.active.displayName, 'Active');
      expect(LeaseStatus.expiring.displayName, 'Expiring');
      expect(LeaseStatus.expired.displayName, 'Expired');
      expect(LeaseStatus.terminated.displayName, 'Terminated');
      expect(LeaseStatus.renewed.displayName, 'Renewed');
    });

    test('should have all enum values', () {
      expect(LeaseStatus.values.length, 6);
    });
  });

  group('LeaseType Enum', () {
    test('should have correct display names', () {
      expect(LeaseType.fixed.displayName, 'Fixed Term');
      expect(LeaseType.monthToMonth.displayName, 'Month-to-Month');
    });

    test('should have all enum values', () {
      expect(LeaseType.values.length, 2);
    });
  });
}
