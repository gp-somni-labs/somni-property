import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/features/work_orders/data/models/work_order_model.dart';
import 'package:somni_property/features/work_orders/data/repositories/work_order_repository_impl.dart';
import 'package:somni_property/features/work_orders/domain/entities/work_order.dart';
import 'package:somni_property/features/work_orders/domain/repositories/work_order_repository.dart';

/// State for work orders list
class WorkOrdersState {
  final List<WorkOrder> workOrders;
  final bool isLoading;
  final String? error;
  final WorkOrderStatsModel? stats;

  const WorkOrdersState({
    this.workOrders = const [],
    this.isLoading = false,
    this.error,
    this.stats,
  });

  WorkOrdersState copyWith({
    List<WorkOrder>? workOrders,
    bool? isLoading,
    String? error,
    WorkOrderStatsModel? stats,
  }) {
    return WorkOrdersState(
      workOrders: workOrders ?? this.workOrders,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      stats: stats ?? this.stats,
    );
  }
}

/// Provider for work orders list
final workOrdersProvider =
    StateNotifierProvider<WorkOrdersNotifier, WorkOrdersState>((ref) {
  final repository = ref.watch(workOrderRepositoryProvider);
  return WorkOrdersNotifier(repository);
});

/// Notifier for managing work orders state
class WorkOrdersNotifier extends StateNotifier<WorkOrdersState> {
  final WorkOrderRepository _repository;

  WorkOrdersNotifier(this._repository) : super(const WorkOrdersState());

  /// Load all work orders
  Future<void> loadWorkOrders({
    String? unitId,
    String? tenantId,
    String? assignedTo,
    WorkOrderStatus? status,
    WorkOrderPriority? priority,
    WorkOrderCategory? category,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getWorkOrders(
      unitId: unitId,
      tenantId: tenantId,
      assignedTo: assignedTo,
      status: status,
      priority: priority,
      category: category,
    );

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (workOrders) => state = state.copyWith(
        isLoading: false,
        workOrders: workOrders,
        stats: WorkOrderStatsModel.fromWorkOrders(workOrders),
      ),
    );
  }

  /// Filter by status
  Future<void> filterByStatus(WorkOrderStatus status) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getWorkOrdersByStatus(status);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (workOrders) => state = state.copyWith(
        isLoading: false,
        workOrders: workOrders,
      ),
    );
  }

  /// Filter by priority
  Future<void> filterByPriority(WorkOrderPriority priority) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getWorkOrdersByPriority(priority);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (workOrders) => state = state.copyWith(
        isLoading: false,
        workOrders: workOrders,
      ),
    );
  }

  /// Get open work orders
  Future<void> loadOpenWorkOrders() async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getOpenWorkOrders();

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (workOrders) => state = state.copyWith(
        isLoading: false,
        workOrders: workOrders,
      ),
    );
  }

  /// Get urgent work orders
  Future<void> loadUrgentWorkOrders() async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getUrgentWorkOrders();

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (workOrders) => state = state.copyWith(
        isLoading: false,
        workOrders: workOrders,
      ),
    );
  }

  /// Create a new work order
  Future<bool> createWorkOrder(WorkOrder workOrder) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.createWorkOrder(workOrder);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (created) {
        state = state.copyWith(
          isLoading: false,
          workOrders: [...state.workOrders, created],
          stats: WorkOrderStatsModel.fromWorkOrders([...state.workOrders, created]),
        );
        return true;
      },
    );
  }

  /// Update a work order
  Future<bool> updateWorkOrder(WorkOrder workOrder) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.updateWorkOrder(workOrder);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (updated) {
        final updatedList = state.workOrders
            .map((wo) => wo.id == updated.id ? updated : wo)
            .toList();
        state = state.copyWith(
          isLoading: false,
          workOrders: updatedList,
          stats: WorkOrderStatsModel.fromWorkOrders(updatedList),
        );
        return true;
      },
    );
  }

  /// Assign work order
  Future<bool> assignWorkOrder(String workOrderId, String assigneeId) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.assignWorkOrder(workOrderId, assigneeId);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (updated) {
        final updatedList = state.workOrders
            .map((wo) => wo.id == updated.id ? updated : wo)
            .toList();
        state = state.copyWith(
          isLoading: false,
          workOrders: updatedList,
        );
        return true;
      },
    );
  }

  /// Update status
  Future<bool> updateStatus(String workOrderId, WorkOrderStatus status) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.updateStatus(workOrderId, status);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (updated) {
        final updatedList = state.workOrders
            .map((wo) => wo.id == updated.id ? updated : wo)
            .toList();
        state = state.copyWith(
          isLoading: false,
          workOrders: updatedList,
          stats: WorkOrderStatsModel.fromWorkOrders(updatedList),
        );
        return true;
      },
    );
  }

  /// Complete work order
  Future<bool> completeWorkOrder(
    String workOrderId,
    DateTime completedDate,
    double? actualCost,
    String? notes,
  ) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.completeWorkOrder(
      workOrderId,
      completedDate,
      actualCost,
      notes,
    );

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (completed) {
        final updatedList = state.workOrders
            .map((wo) => wo.id == completed.id ? completed : wo)
            .toList();
        state = state.copyWith(
          isLoading: false,
          workOrders: updatedList,
          stats: WorkOrderStatsModel.fromWorkOrders(updatedList),
        );
        return true;
      },
    );
  }

  /// Cancel work order
  Future<bool> cancelWorkOrder(String workOrderId, String reason) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.cancelWorkOrder(workOrderId, reason);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (cancelled) {
        final updatedList = state.workOrders
            .map((wo) => wo.id == cancelled.id ? cancelled : wo)
            .toList();
        state = state.copyWith(
          isLoading: false,
          workOrders: updatedList,
          stats: WorkOrderStatsModel.fromWorkOrders(updatedList),
        );
        return true;
      },
    );
  }

  /// Delete a work order
  Future<bool> deleteWorkOrder(String id) async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.deleteWorkOrder(id);

    return result.fold(
      (failure) {
        state = state.copyWith(isLoading: false, error: failure.message);
        return false;
      },
      (_) {
        final updatedList = state.workOrders.where((wo) => wo.id != id).toList();
        state = state.copyWith(
          isLoading: false,
          workOrders: updatedList,
          stats: WorkOrderStatsModel.fromWorkOrders(updatedList),
        );
        return true;
      },
    );
  }
}

/// State for single work order detail
class WorkOrderDetailState {
  final WorkOrder? workOrder;
  final bool isLoading;
  final String? error;

  const WorkOrderDetailState({
    this.workOrder,
    this.isLoading = false,
    this.error,
  });

  WorkOrderDetailState copyWith({
    WorkOrder? workOrder,
    bool? isLoading,
    String? error,
  }) {
    return WorkOrderDetailState(
      workOrder: workOrder ?? this.workOrder,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Provider for single work order detail
final workOrderDetailProvider = StateNotifierProvider.family<
    WorkOrderDetailNotifier, WorkOrderDetailState, String>((ref, workOrderId) {
  final repository = ref.watch(workOrderRepositoryProvider);
  return WorkOrderDetailNotifier(repository, workOrderId);
});

/// Notifier for single work order detail
class WorkOrderDetailNotifier extends StateNotifier<WorkOrderDetailState> {
  final WorkOrderRepository _repository;
  final String _workOrderId;

  WorkOrderDetailNotifier(this._repository, this._workOrderId)
      : super(const WorkOrderDetailState()) {
    loadWorkOrder();
  }

  /// Load work order details
  Future<void> loadWorkOrder() async {
    state = state.copyWith(isLoading: true, error: null);

    final result = await _repository.getWorkOrder(_workOrderId);

    result.fold(
      (failure) => state = state.copyWith(
        isLoading: false,
        error: failure.message,
      ),
      (workOrder) => state = state.copyWith(
        isLoading: false,
        workOrder: workOrder,
      ),
    );
  }

  /// Refresh work order details
  Future<void> refresh() => loadWorkOrder();
}
