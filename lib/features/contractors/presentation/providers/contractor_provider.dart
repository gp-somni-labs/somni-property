import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/features/contractors/data/models/contractor_model.dart';
import 'package:somni_property/features/contractors/data/repositories/contractor_repository_impl.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';
import 'package:somni_property/features/contractors/domain/repositories/contractor_repository.dart';

/// State for contractors list
class ContractorsState {
  final List<Contractor> contractors;
  final bool isLoading;
  final String? error;
  final ContractorStatsModel? stats;

  const ContractorsState({
    this.contractors = const [],
    this.isLoading = false,
    this.error,
    this.stats,
  });

  ContractorsState copyWith({
    List<Contractor>? contractors,
    bool? isLoading,
    String? error,
    ContractorStatsModel? stats,
  }) {
    return ContractorsState(
      contractors: contractors ?? this.contractors,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      stats: stats ?? this.stats,
    );
  }
}

/// Provider for contractors list
final contractorsProvider =
    StateNotifierProvider<ContractorsNotifier, ContractorsState>((ref) {
  final repository = ref.watch(contractorRepositoryProvider);
  return ContractorsNotifier(repository);
});

/// Notifier for managing contractors state
class ContractorsNotifier extends StateNotifier<ContractorsState> {
  final ContractorRepository _repository;

  ContractorsNotifier(this._repository) : super(const ContractorsState());

  /// Load all contractors
  Future<void> loadContractors({String? propertyId}) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getContractors(propertyId: propertyId);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (contractors) => state = state.copyWith(
        isLoading: false,
        contractors: contractors,
        stats: ContractorStatsModel.fromContractors(contractors),
      ),
    );
  }

  /// Search contractors
  Future<void> searchContractors(String query) async {
    if (query.isEmpty) {
      await loadContractors();
      return;
    }

    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.searchContractors(query);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (contractors) => state = state.copyWith(
        isLoading: false,
        contractors: contractors,
      ),
    );
  }

  /// Filter by status
  Future<void> filterByStatus(ContractorStatus status) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getContractorsByStatus(status);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (contractors) => state = state.copyWith(
        isLoading: false,
        contractors: contractors,
      ),
    );
  }

  /// Filter by specialty
  Future<void> filterBySpecialty(String specialty) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getContractorsBySpecialty(specialty);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (contractors) => state = state.copyWith(
        isLoading: false,
        contractors: contractors,
      ),
    );
  }

  /// Get available contractors
  Future<void> loadAvailableContractors() async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getAvailableContractors();

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (contractors) => state = state.copyWith(
        isLoading: false,
        contractors: contractors,
      ),
    );
  }

  /// Create a new contractor
  Future<bool> createContractor(Contractor contractor) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.createContractor(contractor);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (created) {
        state = state.copyWith(
          isLoading: false,
          contractors: [...state.contractors, created],
          stats: ContractorStatsModel.fromContractors(
              [...state.contractors, created]),
        );
        return true;
      },
    );
  }

  /// Update a contractor
  Future<bool> updateContractor(Contractor contractor) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.updateContractor(contractor);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (updated) {
        final updatedList = state.contractors
            .map((c) => c.id == updated.id ? updated : c)
            .toList();
        state = state.copyWith(
          isLoading: false,
          contractors: updatedList,
          stats: ContractorStatsModel.fromContractors(updatedList),
        );
        return true;
      },
    );
  }

  /// Delete a contractor
  Future<bool> deleteContractor(String id) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.deleteContractor(id);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (_) {
        final updatedList =
            state.contractors.where((c) => c.id != id).toList();
        state = state.copyWith(
          isLoading: false,
          contractors: updatedList,
          stats: ContractorStatsModel.fromContractors(updatedList),
        );
        return true;
      },
    );
  }

  /// Assign contractor to work order
  Future<bool> assignToWorkOrder({
    required String contractorId,
    required String workOrderId,
    required double estimatedHours,
    DateTime? startDate,
    String? notes,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.assignToWorkOrder(
      contractorId: contractorId,
      workOrderId: workOrderId,
      estimatedHours: estimatedHours,
      startDate: startDate,
      notes: notes,
    );

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (_) {
        state = state.copyWith(isLoading: false);
        return true;
      },
    );
  }

  /// Track labor time
  Future<bool> trackLaborTime({
    required String contractorId,
    required String workOrderId,
    required DateTime date,
    required double hoursWorked,
    required double overtimeHours,
    String? description,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.trackLaborTime(
      contractorId: contractorId,
      workOrderId: workOrderId,
      date: date,
      hoursWorked: hoursWorked,
      overtimeHours: overtimeHours,
      description: description,
    );

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (_) {
        state = state.copyWith(isLoading: false);
        return true;
      },
    );
  }

  /// Rate contractor
  Future<bool> rateContractor({
    required String contractorId,
    required String workOrderId,
    required int rating,
    required int qualityRating,
    required int communicationRating,
    required int timelinessRating,
    String? review,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.rateContractor(
      contractorId: contractorId,
      workOrderId: workOrderId,
      rating: rating,
      qualityRating: qualityRating,
      communicationRating: communicationRating,
      timelinessRating: timelinessRating,
      review: review,
    );

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (_) {
        state = state.copyWith(isLoading: false);
        // Reload contractors to get updated ratings
        loadContractors();
        return true;
      },
    );
  }
}

/// State for single contractor detail
class ContractorDetailState {
  final Contractor? contractor;
  final ContractorPerformance? performance;
  final List<ContractorRating> ratings;
  final List<LaborTime> laborTimeEntries;
  final List<dynamic> workOrders;
  final bool isLoading;
  final String? error;

  const ContractorDetailState({
    this.contractor,
    this.performance,
    this.ratings = const [],
    this.laborTimeEntries = const [],
    this.workOrders = const [],
    this.isLoading = false,
    this.error,
  });

  ContractorDetailState copyWith({
    Contractor? contractor,
    ContractorPerformance? performance,
    List<ContractorRating>? ratings,
    List<LaborTime>? laborTimeEntries,
    List<dynamic>? workOrders,
    bool? isLoading,
    String? error,
  }) {
    return ContractorDetailState(
      contractor: contractor ?? this.contractor,
      performance: performance ?? this.performance,
      ratings: ratings ?? this.ratings,
      laborTimeEntries: laborTimeEntries ?? this.laborTimeEntries,
      workOrders: workOrders ?? this.workOrders,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Provider for single contractor detail
final contractorDetailProvider = StateNotifierProvider.family<
    ContractorDetailNotifier, ContractorDetailState, String>((ref, contractorId) {
  final repository = ref.watch(contractorRepositoryProvider);
  return ContractorDetailNotifier(repository, contractorId);
});

/// Notifier for single contractor detail
class ContractorDetailNotifier extends StateNotifier<ContractorDetailState> {
  final ContractorRepository _repository;
  final String _contractorId;

  ContractorDetailNotifier(this._repository, this._contractorId)
      : super(const ContractorDetailState()) {
    loadContractor();
  }

  /// Load contractor details
  Future<void> loadContractor() async {
    state = state.copyWith(isLoading: true, error: null);

    // Load contractor basic info
    final contractorResult = await _repository.getContractor(_contractorId);

    contractorResult.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (contractor) async {
        state = state.copyWith(contractor: contractor);

        // Load performance metrics
        final performanceResult =
            await _repository.getContractorPerformance(_contractorId);
        performanceResult.fold(
          (failure) {}, // Silent fail for performance
          (performance) =>
              state = state.copyWith(performance: performance),
        );

        // Load ratings
        final ratingsResult =
            await _repository.getContractorRatings(_contractorId);
        ratingsResult.fold(
          (failure) {},
          (ratings) => state = state.copyWith(ratings: ratings),
        );

        // Load work orders
        final workOrdersResult = await _repository.getContractorWorkOrders(
          contractorId: _contractorId,
        );
        workOrdersResult.fold(
          (failure) {},
          (workOrders) => state = state.copyWith(workOrders: workOrders),
        );

        // Load labor time entries
        final laborTimeResult = await _repository.getLaborTimeEntries(
          contractorId: _contractorId,
        );
        laborTimeResult.fold(
          (failure) {},
          (laborTime) => state = state.copyWith(laborTimeEntries: laborTime),
        );

        state = state.copyWith(isLoading: false);
      },
    );
  }

  /// Refresh contractor details
  Future<void> refresh() => loadContractor();

  /// Update availability
  Future<bool> updateAvailability(Availability availability) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.updateAvailability(
      contractorId: _contractorId,
      availability: availability,
    );

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (updated) {
        state = state.copyWith(
          isLoading: false,
          contractor: updated,
        );
        return true;
      },
    );
  }
}
