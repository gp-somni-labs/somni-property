import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/features/leases/data/models/lease_model.dart';
import 'package:somni_property/features/leases/data/repositories/lease_repository_impl.dart';
import 'package:somni_property/features/leases/domain/entities/lease.dart';
import 'package:somni_property/features/leases/domain/repositories/lease_repository.dart';

/// State for lease list
class LeasesState {
  final List<Lease> leases;
  final bool isLoading;
  final String? error;
  final LeaseStatsModel? stats;

  const LeasesState({
    this.leases = const [],
    this.isLoading = false,
    this.error,
    this.stats,
  });

  LeasesState copyWith({
    List<Lease>? leases,
    bool? isLoading,
    String? error,
    LeaseStatsModel? stats,
  }) {
    return LeasesState(
      leases: leases ?? this.leases,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      stats: stats ?? this.stats,
    );
  }
}

/// Provider for leases list
final leasesProvider =
    StateNotifierProvider<LeasesNotifier, LeasesState>((ref) {
  final repository = ref.watch(leaseRepositoryProvider);
  return LeasesNotifier(repository);
});

/// Notifier for managing leases state
class LeasesNotifier extends StateNotifier<LeasesState> {
  final LeaseRepository _repository;

  LeasesNotifier(this._repository) : super(const LeasesState());

  /// Load all leases
  Future<void> loadLeases({String? propertyId, String? tenantId}) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getLeases(
      propertyId: propertyId,
      tenantId: tenantId,
    );

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (leases) => state = state.copyWith(
        isLoading: false,
        leases: leases,
        stats: LeaseStatsModel.fromLeases(leases),
      ),
    );
  }

  /// Filter by status
  Future<void> filterByStatus(LeaseStatus status) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getLeasesByStatus(status);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (leases) => state = state.copyWith(
        isLoading: false,
        leases: leases,
      ),
    );
  }

  /// Get expiring leases
  Future<void> loadExpiringLeases({int withinDays = 30}) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getExpiringLeases(withinDays);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (leases) => state = state.copyWith(
        isLoading: false,
        leases: leases,
      ),
    );
  }

  /// Create a new lease
  Future<bool> createLease(Lease lease) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.createLease(lease);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (created) {
        state = state.copyWith(
          isLoading: false,
          leases: [...state.leases, created],
          stats: LeaseStatsModel.fromLeases([...state.leases, created]),
        );
        return true;
      },
    );
  }

  /// Update a lease
  Future<bool> updateLease(Lease lease) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.updateLease(lease);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (updated) {
        final updatedList = state.leases
            .map((l) => l.id == updated.id ? updated : l)
            .toList();
        state = state.copyWith(
          isLoading: false,
          leases: updatedList,
          stats: LeaseStatsModel.fromLeases(updatedList),
        );
        return true;
      },
    );
  }

  /// Delete a lease
  Future<bool> deleteLease(String id) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.deleteLease(id);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (_) {
        final updatedList = state.leases.where((l) => l.id != id).toList();
        state = state.copyWith(
          isLoading: false,
          leases: updatedList,
          stats: LeaseStatsModel.fromLeases(updatedList),
        );
        return true;
      },
    );
  }

  /// Renew a lease
  Future<bool> renewLease(String id, DateTime newEndDate, double? newRent) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.renewLease(id, newEndDate, newRent);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (renewed) {
        final updatedList = state.leases
            .map((l) => l.id == renewed.id ? renewed : l)
            .toList();
        state = state.copyWith(
          isLoading: false,
          leases: updatedList,
          stats: LeaseStatsModel.fromLeases(updatedList),
        );
        return true;
      },
    );
  }

  /// Terminate a lease
  Future<bool> terminateLease(String id, DateTime terminationDate, String reason) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.terminateLease(id, terminationDate, reason);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (terminated) {
        final updatedList = state.leases
            .map((l) => l.id == terminated.id ? terminated : l)
            .toList();
        state = state.copyWith(
          isLoading: false,
          leases: updatedList,
          stats: LeaseStatsModel.fromLeases(updatedList),
        );
        return true;
      },
    );
  }
}

/// State for single lease detail
class LeaseDetailState {
  final Lease? lease;
  final bool isLoading;
  final String? error;

  const LeaseDetailState({
    this.lease,
    this.isLoading = false,
    this.error,
  });

  LeaseDetailState copyWith({
    Lease? lease,
    bool? isLoading,
    String? error,
  }) {
    return LeaseDetailState(
      lease: lease ?? this.lease,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Provider for single lease detail
final leaseDetailProvider = StateNotifierProvider.family<LeaseDetailNotifier,
    LeaseDetailState, String>((ref, leaseId) {
  final repository = ref.watch(leaseRepositoryProvider);
  return LeaseDetailNotifier(repository, leaseId);
});

/// Notifier for single lease detail
class LeaseDetailNotifier extends StateNotifier<LeaseDetailState> {
  final LeaseRepository _repository;
  final String _leaseId;

  LeaseDetailNotifier(this._repository, this._leaseId)
      : super(const LeaseDetailState()) {
    loadLease();
  }

  /// Load lease details
  Future<void> loadLease() async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getLease(_leaseId);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (lease) => state = state.copyWith(
        isLoading: false,
        lease: lease,
      ),
    );
  }

  /// Refresh lease details
  Future<void> refresh() => loadLease();
}
