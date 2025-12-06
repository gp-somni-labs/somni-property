import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/features/payments/data/models/payment_model.dart';
import 'package:somni_property/features/payments/data/repositories/payment_repository_impl.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';
import 'package:somni_property/features/payments/domain/repositories/payment_repository.dart';

/// State for payments list
class PaymentsState {
  final List<Payment> payments;
  final bool isLoading;
  final String? error;
  final PaymentStatsModel? stats;

  const PaymentsState({
    this.payments = const [],
    this.isLoading = false,
    this.error,
    this.stats,
  });

  PaymentsState copyWith({
    List<Payment>? payments,
    bool? isLoading,
    String? error,
    PaymentStatsModel? stats,
  }) {
    return PaymentsState(
      payments: payments ?? this.payments,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      stats: stats ?? this.stats,
    );
  }
}

/// Provider for payments list
final paymentsProvider =
    StateNotifierProvider<PaymentsNotifier, PaymentsState>((ref) {
  final repository = ref.watch(paymentRepositoryProvider);
  return PaymentsNotifier(repository);
});

/// Notifier for managing payments state
class PaymentsNotifier extends StateNotifier<PaymentsState> {
  final PaymentRepository _repository;

  PaymentsNotifier(this._repository) : super(const PaymentsState());

  /// Load all payments
  Future<void> loadPayments({
    String? leaseId,
    String? tenantId,
    String? unitId,
    PaymentStatus? status,
    PaymentType? type,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getPayments(
      leaseId: leaseId,
      tenantId: tenantId,
      unitId: unitId,
      status: status,
      type: type,
      fromDate: fromDate,
      toDate: toDate,
    );

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (payments) => state = state.copyWith(
        isLoading: false,
        payments: payments,
        stats: PaymentStatsModel.fromPayments(payments),
      ),
    );
  }

  /// Filter by status
  Future<void> filterByStatus(PaymentStatus status) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getPaymentsByStatus(status);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (payments) => state = state.copyWith(
        isLoading: false,
        payments: payments,
      ),
    );
  }

  /// Get overdue payments
  Future<void> loadOverduePayments() async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getOverduePayments();

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (payments) => state = state.copyWith(
        isLoading: false,
        payments: payments,
      ),
    );
  }

  /// Get upcoming payments
  Future<void> loadUpcomingPayments({int withinDays = 7}) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getUpcomingPayments(withinDays);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (payments) => state = state.copyWith(
        isLoading: false,
        payments: payments,
      ),
    );
  }

  /// Create a new payment
  Future<bool> createPayment(Payment payment) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.createPayment(payment);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (created) {
        state = state.copyWith(
          isLoading: false,
          payments: [...state.payments, created],
          stats: PaymentStatsModel.fromPayments([...state.payments, created]),
        );
        return true;
      },
    );
  }

  /// Update a payment
  Future<bool> updatePayment(Payment payment) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.updatePayment(payment);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (updated) {
        final updatedList = state.payments
            .map((p) => p.id == updated.id ? updated : p)
            .toList();
        state = state.copyWith(
          isLoading: false,
          payments: updatedList,
          stats: PaymentStatsModel.fromPayments(updatedList),
        );
        return true;
      },
    );
  }

  /// Record a payment
  Future<bool> recordPayment(
    String paymentId,
    DateTime paidDate,
    PaymentMethod method,
    String? transactionId,
  ) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.recordPayment(
      paymentId,
      paidDate,
      method,
      transactionId,
    );

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (recorded) {
        final updatedList = state.payments
            .map((p) => p.id == recorded.id ? recorded : p)
            .toList();
        state = state.copyWith(
          isLoading: false,
          payments: updatedList,
          stats: PaymentStatsModel.fromPayments(updatedList),
        );
        return true;
      },
    );
  }

  /// Apply late fee
  Future<bool> applyLateFee(String paymentId, double amount) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.applyLateFee(paymentId, amount);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (updated) {
        final updatedList = state.payments
            .map((p) => p.id == updated.id ? updated : p)
            .toList();
        state = state.copyWith(
          isLoading: false,
          payments: updatedList,
          stats: PaymentStatsModel.fromPayments(updatedList),
        );
        return true;
      },
    );
  }

  /// Cancel a payment
  Future<bool> cancelPayment(String paymentId, String reason) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.cancelPayment(paymentId, reason);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (cancelled) {
        final updatedList = state.payments
            .map((p) => p.id == cancelled.id ? cancelled : p)
            .toList();
        state = state.copyWith(
          isLoading: false,
          payments: updatedList,
          stats: PaymentStatsModel.fromPayments(updatedList),
        );
        return true;
      },
    );
  }

  /// Refund a payment
  Future<bool> refundPayment(String paymentId, String reason) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.refundPayment(paymentId, reason);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (refunded) {
        final updatedList = state.payments
            .map((p) => p.id == refunded.id ? refunded : p)
            .toList();
        state = state.copyWith(
          isLoading: false,
          payments: updatedList,
          stats: PaymentStatsModel.fromPayments(updatedList),
        );
        return true;
      },
    );
  }

  /// Delete a payment
  Future<bool> deletePayment(String id) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.deletePayment(id);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (_) {
        final updatedList = state.payments.where((p) => p.id != id).toList();
        state = state.copyWith(
          isLoading: false,
          payments: updatedList,
          stats: PaymentStatsModel.fromPayments(updatedList),
        );
        return true;
      },
    );
  }
}

/// State for single payment detail
class PaymentDetailState {
  final Payment? payment;
  final bool isLoading;
  final String? error;

  const PaymentDetailState({
    this.payment,
    this.isLoading = false,
    this.error,
  });

  PaymentDetailState copyWith({
    Payment? payment,
    bool? isLoading,
    String? error,
  }) {
    return PaymentDetailState(
      payment: payment ?? this.payment,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Provider for single payment detail
final paymentDetailProvider = StateNotifierProvider.family<
    PaymentDetailNotifier, PaymentDetailState, String>((ref, paymentId) {
  final repository = ref.watch(paymentRepositoryProvider);
  return PaymentDetailNotifier(repository, paymentId);
});

/// Notifier for single payment detail
class PaymentDetailNotifier extends StateNotifier<PaymentDetailState> {
  final PaymentRepository _repository;
  final String _paymentId;

  PaymentDetailNotifier(this._repository, this._paymentId)
      : super(const PaymentDetailState()) {
    loadPayment();
  }

  /// Load payment details
  Future<void> loadPayment() async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getPayment(_paymentId);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (payment) => state = state.copyWith(
        isLoading: false,
        payment: payment,
      ),
    );
  }

  /// Refresh payment details
  Future<void> refresh() => loadPayment();
}
