import 'package:somni_property/features/work_orders/domain/entities/work_order.dart';
import 'package:somni_property/features/work_orders/domain/repositories/work_order_repository.dart';

/// Work order model for JSON serialization
class WorkOrderModel extends WorkOrder {
  const WorkOrderModel({
    required super.id,
    required super.unitId,
    super.tenantId,
    required super.title,
    required super.description,
    required super.category,
    required super.priority,
    required super.status,
    required super.createdAt,
    required super.updatedAt,
    super.scheduledDate,
    super.completedDate,
    super.assignedTo,
    super.notes,
    super.estimatedCost,
    super.actualCost,
    super.attachments,
    super.unitNumber,
    super.tenantName,
    super.assignedName,
  });

  /// Create model from JSON
  factory WorkOrderModel.fromJson(Map<String, dynamic> json) {
    return WorkOrderModel(
      id: json['id']?.toString() ?? '',
      unitId: json['unit_id']?.toString() ?? json['unitId']?.toString() ?? '',
      tenantId: json['tenant_id']?.toString() ?? json['tenantId']?.toString(),
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      category: WorkOrderCategory.fromString(
        json['category']?.toString() ?? 'general',
      ),
      priority: WorkOrderPriority.fromString(
        json['priority']?.toString() ?? 'medium',
      ),
      status: WorkOrderStatus.fromString(
        json['status']?.toString() ?? 'open',
      ),
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
      scheduledDate: json['scheduled_date'] != null
          ? DateTime.parse(json['scheduled_date'])
          : json['scheduledDate'] != null
              ? DateTime.parse(json['scheduledDate'])
              : null,
      completedDate: json['completed_date'] != null
          ? DateTime.parse(json['completed_date'])
          : json['completedDate'] != null
              ? DateTime.parse(json['completedDate'])
              : null,
      assignedTo: json['assigned_to']?.toString() ?? json['assignedTo']?.toString(),
      notes: json['notes']?.toString(),
      estimatedCost: (json['estimated_cost'] as num?)?.toDouble() ??
          (json['estimatedCost'] as num?)?.toDouble(),
      actualCost: (json['actual_cost'] as num?)?.toDouble() ??
          (json['actualCost'] as num?)?.toDouble(),
      attachments: json['attachments'] != null
          ? List<String>.from(json['attachments'])
          : null,
      unitNumber: json['unit_number']?.toString() ?? json['unitNumber']?.toString(),
      tenantName: json['tenant_name']?.toString() ?? json['tenantName']?.toString(),
      assignedName: json['assigned_name']?.toString() ?? json['assignedName']?.toString(),
    );
  }

  /// Convert model to JSON for API requests
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'unit_id': unitId,
      if (tenantId != null) 'tenant_id': tenantId,
      'title': title,
      'description': description,
      'category': category.name,
      'priority': priority.name,
      'status': status.name,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      if (scheduledDate != null) 'scheduled_date': scheduledDate!.toIso8601String(),
      if (completedDate != null) 'completed_date': completedDate!.toIso8601String(),
      if (assignedTo != null) 'assigned_to': assignedTo,
      if (notes != null) 'notes': notes,
      if (estimatedCost != null) 'estimated_cost': estimatedCost,
      if (actualCost != null) 'actual_cost': actualCost,
      if (attachments != null) 'attachments': attachments,
    };
  }

  /// Create model from entity
  factory WorkOrderModel.fromEntity(WorkOrder workOrder) {
    return WorkOrderModel(
      id: workOrder.id,
      unitId: workOrder.unitId,
      tenantId: workOrder.tenantId,
      title: workOrder.title,
      description: workOrder.description,
      category: workOrder.category,
      priority: workOrder.priority,
      status: workOrder.status,
      createdAt: workOrder.createdAt,
      updatedAt: workOrder.updatedAt,
      scheduledDate: workOrder.scheduledDate,
      completedDate: workOrder.completedDate,
      assignedTo: workOrder.assignedTo,
      notes: workOrder.notes,
      estimatedCost: workOrder.estimatedCost,
      actualCost: workOrder.actualCost,
      attachments: workOrder.attachments,
      unitNumber: workOrder.unitNumber,
      tenantName: workOrder.tenantName,
      assignedName: workOrder.assignedName,
    );
  }

  /// Convert to entity
  WorkOrder toEntity() {
    return WorkOrder(
      id: id,
      unitId: unitId,
      tenantId: tenantId,
      title: title,
      description: description,
      category: category,
      priority: priority,
      status: status,
      createdAt: createdAt,
      updatedAt: updatedAt,
      scheduledDate: scheduledDate,
      completedDate: completedDate,
      assignedTo: assignedTo,
      notes: notes,
      estimatedCost: estimatedCost,
      actualCost: actualCost,
      attachments: attachments,
      unitNumber: unitNumber,
      tenantName: tenantName,
      assignedName: assignedName,
    );
  }
}

/// Work order statistics model for state management
class WorkOrderStatsModel {
  final int totalWorkOrders;
  final int openWorkOrders;
  final int inProgressWorkOrders;
  final int completedWorkOrders;
  final int urgentWorkOrders;
  final double averageCompletionDays;
  final double totalCost;

  const WorkOrderStatsModel({
    required this.totalWorkOrders,
    required this.openWorkOrders,
    required this.inProgressWorkOrders,
    required this.completedWorkOrders,
    required this.urgentWorkOrders,
    required this.averageCompletionDays,
    required this.totalCost,
  });

  factory WorkOrderStatsModel.empty() => const WorkOrderStatsModel(
        totalWorkOrders: 0,
        openWorkOrders: 0,
        inProgressWorkOrders: 0,
        completedWorkOrders: 0,
        urgentWorkOrders: 0,
        averageCompletionDays: 0,
        totalCost: 0,
      );

  factory WorkOrderStatsModel.fromWorkOrders(List<WorkOrder> workOrders) {
    final stats = WorkOrderStats.fromWorkOrders(workOrders);
    return WorkOrderStatsModel(
      totalWorkOrders: stats.totalWorkOrders,
      openWorkOrders: stats.openWorkOrders,
      inProgressWorkOrders: stats.inProgressWorkOrders,
      completedWorkOrders: stats.completedWorkOrders,
      urgentWorkOrders: stats.urgentWorkOrders,
      averageCompletionDays: stats.averageCompletionDays,
      totalCost: stats.totalCost,
    );
  }

  factory WorkOrderStatsModel.fromJson(Map<String, dynamic> json) {
    return WorkOrderStatsModel(
      totalWorkOrders: json['total_work_orders'] as int? ?? 0,
      openWorkOrders: json['open_work_orders'] as int? ?? 0,
      inProgressWorkOrders: json['in_progress_work_orders'] as int? ?? 0,
      completedWorkOrders: json['completed_work_orders'] as int? ?? 0,
      urgentWorkOrders: json['urgent_work_orders'] as int? ?? 0,
      averageCompletionDays: (json['average_completion_days'] as num?)?.toDouble() ?? 0,
      totalCost: (json['total_cost'] as num?)?.toDouble() ?? 0,
    );
  }
}
