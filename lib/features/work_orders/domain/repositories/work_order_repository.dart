import 'package:dartz/dartz.dart';
import 'package:somni_property/core/error/failures.dart';
import 'package:somni_property/features/work_orders/domain/entities/work_order.dart';

/// Work order repository interface defining data operations
abstract class WorkOrderRepository {
  /// Get all work orders with optional filters
  Future<Either<Failure, List<WorkOrder>>> getWorkOrders({
    String? unitId,
    String? tenantId,
    String? assignedTo,
    WorkOrderStatus? status,
    WorkOrderPriority? priority,
    WorkOrderCategory? category,
  });

  /// Get a single work order by ID
  Future<Either<Failure, WorkOrder>> getWorkOrder(String id);

  /// Get work orders by status
  Future<Either<Failure, List<WorkOrder>>> getWorkOrdersByStatus(
      WorkOrderStatus status);

  /// Get work orders by priority
  Future<Either<Failure, List<WorkOrder>>> getWorkOrdersByPriority(
      WorkOrderPriority priority);

  /// Get open work orders (not completed or cancelled)
  Future<Either<Failure, List<WorkOrder>>> getOpenWorkOrders();

  /// Get work orders for a specific unit
  Future<Either<Failure, List<WorkOrder>>> getWorkOrdersForUnit(String unitId);

  /// Get work orders assigned to a specific person
  Future<Either<Failure, List<WorkOrder>>> getWorkOrdersForAssignee(
      String assigneeId);

  /// Get urgent work orders
  Future<Either<Failure, List<WorkOrder>>> getUrgentWorkOrders();

  /// Create a new work order
  Future<Either<Failure, WorkOrder>> createWorkOrder(WorkOrder workOrder);

  /// Update an existing work order
  Future<Either<Failure, WorkOrder>> updateWorkOrder(WorkOrder workOrder);

  /// Assign work order to someone
  Future<Either<Failure, WorkOrder>> assignWorkOrder(
      String workOrderId, String assigneeId);

  /// Update work order status
  Future<Either<Failure, WorkOrder>> updateStatus(
      String workOrderId, WorkOrderStatus status);

  /// Complete a work order
  Future<Either<Failure, WorkOrder>> completeWorkOrder(
    String workOrderId,
    DateTime completedDate,
    double? actualCost,
    String? notes,
  );

  /// Cancel a work order
  Future<Either<Failure, WorkOrder>> cancelWorkOrder(
      String workOrderId, String reason);

  /// Delete a work order
  Future<Either<Failure, void>> deleteWorkOrder(String id);
}

/// Work order statistics model
class WorkOrderStats {
  final int totalWorkOrders;
  final int openWorkOrders;
  final int inProgressWorkOrders;
  final int completedWorkOrders;
  final int urgentWorkOrders;
  final double averageCompletionDays;
  final double totalCost;

  const WorkOrderStats({
    required this.totalWorkOrders,
    required this.openWorkOrders,
    required this.inProgressWorkOrders,
    required this.completedWorkOrders,
    required this.urgentWorkOrders,
    required this.averageCompletionDays,
    required this.totalCost,
  });

  factory WorkOrderStats.empty() => const WorkOrderStats(
        totalWorkOrders: 0,
        openWorkOrders: 0,
        inProgressWorkOrders: 0,
        completedWorkOrders: 0,
        urgentWorkOrders: 0,
        averageCompletionDays: 0,
        totalCost: 0,
      );

  factory WorkOrderStats.fromWorkOrders(List<WorkOrder> workOrders) {
    int open = 0;
    int inProgress = 0;
    int completed = 0;
    int urgent = 0;
    double totalCost = 0;
    int completedCount = 0;
    int totalDays = 0;

    for (final wo in workOrders) {
      switch (wo.status) {
        case WorkOrderStatus.open:
        case WorkOrderStatus.pending:
          open++;
          break;
        case WorkOrderStatus.inProgress:
          inProgress++;
          break;
        case WorkOrderStatus.completed:
          completed++;
          completedCount++;
          if (wo.completedDate != null) {
            totalDays += wo.completedDate!.difference(wo.createdAt).inDays;
          }
          break;
        default:
          break;
      }

      if (wo.isUrgent) urgent++;
      if (wo.actualCost != null) totalCost += wo.actualCost!;
    }

    final avgDays = completedCount > 0 ? totalDays / completedCount : 0.0;

    return WorkOrderStats(
      totalWorkOrders: workOrders.length,
      openWorkOrders: open,
      inProgressWorkOrders: inProgress,
      completedWorkOrders: completed,
      urgentWorkOrders: urgent,
      averageCompletionDays: avgDays,
      totalCost: totalCost,
    );
  }
}
