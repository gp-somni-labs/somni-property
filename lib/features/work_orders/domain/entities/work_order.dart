import 'package:equatable/equatable.dart';

/// Work order entity representing a maintenance request
class WorkOrder extends Equatable {
  final String id;
  final String unitId;
  final String? tenantId;
  final String title;
  final String description;
  final WorkOrderCategory category;
  final WorkOrderPriority priority;
  final WorkOrderStatus status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? scheduledDate;
  final DateTime? completedDate;
  final String? assignedTo;
  final String? notes;
  final double? estimatedCost;
  final double? actualCost;
  final List<String>? attachments;

  // Joined data
  final String? unitNumber;
  final String? tenantName;
  final String? assignedName;

  const WorkOrder({
    required this.id,
    required this.unitId,
    this.tenantId,
    required this.title,
    required this.description,
    required this.category,
    required this.priority,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.scheduledDate,
    this.completedDate,
    this.assignedTo,
    this.notes,
    this.estimatedCost,
    this.actualCost,
    this.attachments,
    this.unitNumber,
    this.tenantName,
    this.assignedName,
  });

  /// Check if work order is open
  bool get isOpen =>
      status == WorkOrderStatus.open ||
      status == WorkOrderStatus.inProgress ||
      status == WorkOrderStatus.pending;

  /// Check if work order is urgent
  bool get isUrgent =>
      priority == WorkOrderPriority.urgent ||
      priority == WorkOrderPriority.emergency;

  /// Get days since created
  int get daysSinceCreated =>
      DateTime.now().difference(createdAt).inDays;

  /// Get formatted scheduled date
  String? get formattedScheduledDate => scheduledDate != null
      ? '${scheduledDate!.month}/${scheduledDate!.day}/${scheduledDate!.year}'
      : null;

  /// Get formatted completed date
  String? get formattedCompletedDate => completedDate != null
      ? '${completedDate!.month}/${completedDate!.day}/${completedDate!.year}'
      : null;

  /// Get formatted created date
  String get formattedCreatedDate =>
      '${createdAt.month}/${createdAt.day}/${createdAt.year}';

  /// Copy with new values
  WorkOrder copyWith({
    String? id,
    String? unitId,
    String? tenantId,
    String? title,
    String? description,
    WorkOrderCategory? category,
    WorkOrderPriority? priority,
    WorkOrderStatus? status,
    DateTime? createdAt,
    DateTime? updatedAt,
    DateTime? scheduledDate,
    DateTime? completedDate,
    String? assignedTo,
    String? notes,
    double? estimatedCost,
    double? actualCost,
    List<String>? attachments,
    String? unitNumber,
    String? tenantName,
    String? assignedName,
  }) {
    return WorkOrder(
      id: id ?? this.id,
      unitId: unitId ?? this.unitId,
      tenantId: tenantId ?? this.tenantId,
      title: title ?? this.title,
      description: description ?? this.description,
      category: category ?? this.category,
      priority: priority ?? this.priority,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      scheduledDate: scheduledDate ?? this.scheduledDate,
      completedDate: completedDate ?? this.completedDate,
      assignedTo: assignedTo ?? this.assignedTo,
      notes: notes ?? this.notes,
      estimatedCost: estimatedCost ?? this.estimatedCost,
      actualCost: actualCost ?? this.actualCost,
      attachments: attachments ?? this.attachments,
      unitNumber: unitNumber ?? this.unitNumber,
      tenantName: tenantName ?? this.tenantName,
      assignedName: assignedName ?? this.assignedName,
    );
  }

  @override
  List<Object?> get props => [
        id,
        unitId,
        tenantId,
        title,
        description,
        category,
        priority,
        status,
        createdAt,
        updatedAt,
        scheduledDate,
        completedDate,
        assignedTo,
        notes,
        estimatedCost,
        actualCost,
        attachments,
      ];
}

/// Work order category enumeration
enum WorkOrderCategory {
  plumbing,
  electrical,
  hvac,
  appliance,
  structural,
  pest,
  cleaning,
  landscaping,
  security,
  general,
  other;

  String get displayName {
    switch (this) {
      case WorkOrderCategory.plumbing:
        return 'Plumbing';
      case WorkOrderCategory.electrical:
        return 'Electrical';
      case WorkOrderCategory.hvac:
        return 'HVAC';
      case WorkOrderCategory.appliance:
        return 'Appliance';
      case WorkOrderCategory.structural:
        return 'Structural';
      case WorkOrderCategory.pest:
        return 'Pest Control';
      case WorkOrderCategory.cleaning:
        return 'Cleaning';
      case WorkOrderCategory.landscaping:
        return 'Landscaping';
      case WorkOrderCategory.security:
        return 'Security';
      case WorkOrderCategory.general:
        return 'General';
      case WorkOrderCategory.other:
        return 'Other';
    }
  }

  static WorkOrderCategory fromString(String value) {
    return WorkOrderCategory.values.firstWhere(
      (cat) => cat.name.toLowerCase() == value.toLowerCase(),
      orElse: () => WorkOrderCategory.general,
    );
  }
}

/// Work order priority enumeration
enum WorkOrderPriority {
  low,
  medium,
  high,
  urgent,
  emergency;

  String get displayName {
    switch (this) {
      case WorkOrderPriority.low:
        return 'Low';
      case WorkOrderPriority.medium:
        return 'Medium';
      case WorkOrderPriority.high:
        return 'High';
      case WorkOrderPriority.urgent:
        return 'Urgent';
      case WorkOrderPriority.emergency:
        return 'Emergency';
    }
  }

  static WorkOrderPriority fromString(String value) {
    return WorkOrderPriority.values.firstWhere(
      (priority) => priority.name.toLowerCase() == value.toLowerCase(),
      orElse: () => WorkOrderPriority.medium,
    );
  }
}

/// Work order status enumeration
enum WorkOrderStatus {
  open,
  pending,
  inProgress,
  onHold,
  completed,
  cancelled;

  String get displayName {
    switch (this) {
      case WorkOrderStatus.open:
        return 'Open';
      case WorkOrderStatus.pending:
        return 'Pending';
      case WorkOrderStatus.inProgress:
        return 'In Progress';
      case WorkOrderStatus.onHold:
        return 'On Hold';
      case WorkOrderStatus.completed:
        return 'Completed';
      case WorkOrderStatus.cancelled:
        return 'Cancelled';
    }
  }

  static WorkOrderStatus fromString(String value) {
    switch (value.toLowerCase().replaceAll('_', '').replaceAll(' ', '')) {
      case 'open':
        return WorkOrderStatus.open;
      case 'pending':
        return WorkOrderStatus.pending;
      case 'inprogress':
        return WorkOrderStatus.inProgress;
      case 'onhold':
        return WorkOrderStatus.onHold;
      case 'completed':
        return WorkOrderStatus.completed;
      case 'cancelled':
      case 'canceled':
        return WorkOrderStatus.cancelled;
      default:
        return WorkOrderStatus.open;
    }
  }
}
