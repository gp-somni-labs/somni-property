import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/features/tenants/data/models/tenant_model.dart';
import 'package:somni_property/features/tenants/data/repositories/tenant_repository_impl.dart';
import 'package:somni_property/features/tenants/domain/entities/tenant.dart';
import 'package:somni_property/features/tenants/domain/repositories/tenant_repository.dart';

/// State for tenant list
class TenantsState {
  final List<Tenant> tenants;
  final bool isLoading;
  final String? error;
  final TenantStatsModel? stats;

  const TenantsState({
    this.tenants = const [],
    this.isLoading = false,
    this.error,
    this.stats,
  });

  TenantsState copyWith({
    List<Tenant>? tenants,
    bool? isLoading,
    String? error,
    TenantStatsModel? stats,
  }) {
    return TenantsState(
      tenants: tenants ?? this.tenants,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      stats: stats ?? this.stats,
    );
  }
}

/// Provider for tenants list
final tenantsProvider =
    StateNotifierProvider<TenantsNotifier, TenantsState>((ref) {
  final repository = ref.watch(tenantRepositoryProvider);
  return TenantsNotifier(repository);
});

/// Notifier for managing tenants state
class TenantsNotifier extends StateNotifier<TenantsState> {
  final TenantRepository _repository;

  TenantsNotifier(this._repository) : super(const TenantsState());

  /// Load all tenants
  Future<void> loadTenants({String? propertyId}) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getTenants(propertyId: propertyId);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (tenants) => state = state.copyWith(
        isLoading: false,
        tenants: tenants,
        stats: TenantStatsModel.fromTenants(tenants),
      ),
    );
  }

  /// Search tenants
  Future<void> searchTenants(String query) async {
    if (query.isEmpty) {
      await loadTenants();
      return;
    }

    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.searchTenants(query);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (tenants) => state = state.copyWith(
        isLoading: false,
        tenants: tenants,
      ),
    );
  }

  /// Filter by status
  Future<void> filterByStatus(TenantStatus status) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getTenantsByStatus(status);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (tenants) => state = state.copyWith(
        isLoading: false,
        tenants: tenants,
      ),
    );
  }

  /// Create a new tenant
  Future<bool> createTenant(Tenant tenant) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.createTenant(tenant);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (created) {
        state = state.copyWith(
          isLoading: false,
          tenants: [...state.tenants, created],
          stats: TenantStatsModel.fromTenants([...state.tenants, created]),
        );
        return true;
      },
    );
  }

  /// Update a tenant
  Future<bool> updateTenant(Tenant tenant) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.updateTenant(tenant);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (updated) {
        final updatedList = state.tenants
            .map((t) => t.id == updated.id ? updated : t)
            .toList();
        state = state.copyWith(
          isLoading: false,
          tenants: updatedList,
          stats: TenantStatsModel.fromTenants(updatedList),
        );
        return true;
      },
    );
  }

  /// Delete a tenant
  Future<bool> deleteTenant(String id) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.deleteTenant(id);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (_) {
        final updatedList =
            state.tenants.where((t) => t.id != id).toList();
        state = state.copyWith(
          isLoading: false,
          tenants: updatedList,
          stats: TenantStatsModel.fromTenants(updatedList),
        );
        return true;
      },
    );
  }
}

/// State for single tenant detail
class TenantDetailState {
  final Tenant? tenant;
  final bool isLoading;
  final String? error;

  const TenantDetailState({
    this.tenant,
    this.isLoading = false,
    this.error,
  });

  TenantDetailState copyWith({
    Tenant? tenant,
    bool? isLoading,
    String? error,
  }) {
    return TenantDetailState(
      tenant: tenant ?? this.tenant,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Provider for single tenant detail
final tenantDetailProvider = StateNotifierProvider.family<TenantDetailNotifier,
    TenantDetailState, String>((ref, tenantId) {
  final repository = ref.watch(tenantRepositoryProvider);
  return TenantDetailNotifier(repository, tenantId);
});

/// Notifier for single tenant detail
class TenantDetailNotifier extends StateNotifier<TenantDetailState> {
  final TenantRepository _repository;
  final String _tenantId;

  TenantDetailNotifier(this._repository, this._tenantId)
      : super(const TenantDetailState()) {
    loadTenant();
  }

  /// Load tenant details
  Future<void> loadTenant() async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getTenant(_tenantId);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (tenant) => state = state.copyWith(
        isLoading: false,
        tenant: tenant,
      ),
    );
  }

  /// Refresh tenant details
  Future<void> refresh() => loadTenant();
}
