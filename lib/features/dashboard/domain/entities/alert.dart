import 'package:equatable/equatable.dart';

/// Alert entity for urgent notifications on dashboard
class Alert extends Equatable {
  final String id;
  final String title;
  final String message;
  final AlertPriority priority;
  final AlertType type;
  final DateTime createdAt;
  final String? actionUrl;
  final String? actionLabel;
  final String? relatedEntityId;
  final String? relatedEntityType;
  final bool isDismissible;

  const Alert({
    required this.id,
    required this.title,
    required this.message,
    required this.priority,
    required this.type,
    required this.createdAt,
    this.actionUrl,
    this.actionLabel,
    this.relatedEntityId,
    this.relatedEntityType,
    this.isDismissible = true,
  });

  /// Get time remaining for time-sensitive alerts
  String? get timeRemaining {
    if (type == AlertType.leaseExpiring ||
        type == AlertType.paymentDue ||
        type == AlertType.maintenanceScheduled) {
      final now = DateTime.now();
      final difference = createdAt.difference(now);

      if (difference.inDays > 0) {
        return '${difference.inDays} ${difference.inDays == 1 ? 'day' : 'days'}';
      } else if (difference.inHours > 0) {
        return '${difference.inHours} ${difference.inHours == 1 ? 'hour' : 'hours'}';
      } else {
        return 'Soon';
      }
    }
    return null;
  }

  @override
  List<Object?> get props => [
        id,
        title,
        message,
        priority,
        type,
        createdAt,
        actionUrl,
        actionLabel,
        relatedEntityId,
        relatedEntityType,
        isDismissible,
      ];
}

/// Alert priority levels
enum AlertPriority {
  critical('critical', 'Critical'),
  high('high', 'High'),
  medium('medium', 'Medium'),
  low('low', 'Low');

  final String value;
  final String displayName;

  const AlertPriority(this.value, this.displayName);

  static AlertPriority fromString(String value) {
    return AlertPriority.values.firstWhere(
      (priority) => priority.value == value,
      orElse: () => AlertPriority.medium,
    );
  }
}

/// Types of alerts
enum AlertType {
  leaseExpiring('lease_expiring', 'Lease Expiring'),
  paymentDue('payment_due', 'Payment Due'),
  paymentOverdue('payment_overdue', 'Payment Overdue'),
  maintenanceRequired('maintenance_required', 'Maintenance Required'),
  maintenanceScheduled('maintenance_scheduled', 'Maintenance Scheduled'),
  workOrderCritical('work_order_critical', 'Critical Work Order'),
  documentExpiring('document_expiring', 'Document Expiring'),
  inspectionDue('inspection_due', 'Inspection Due'),
  complianceIssue('compliance_issue', 'Compliance Issue'),
  systemNotification('system_notification', 'System Notification');

  final String value;
  final String displayName;

  const AlertType(this.value, this.displayName);

  static AlertType fromString(String value) {
    return AlertType.values.firstWhere(
      (type) => type.value == value,
      orElse: () => AlertType.systemNotification,
    );
  }
}

/// Upcoming event entity
class UpcomingEvent extends Equatable {
  final String id;
  final String title;
  final String description;
  final DateTime scheduledDate;
  final EventType type;
  final String? relatedEntityId;
  final String? relatedEntityType;

  const UpcomingEvent({
    required this.id,
    required this.title,
    required this.description,
    required this.scheduledDate,
    required this.type,
    this.relatedEntityId,
    this.relatedEntityType,
  });

  /// Get days until event
  int get daysUntil {
    final now = DateTime.now();
    final difference = scheduledDate.difference(now);
    return difference.inDays;
  }

  @override
  List<Object?> get props => [
        id,
        title,
        description,
        scheduledDate,
        type,
        relatedEntityId,
        relatedEntityType,
      ];
}

/// Types of upcoming events
enum EventType {
  leaseRenewal('lease_renewal', 'Lease Renewal'),
  inspection('inspection', 'Inspection'),
  maintenance('maintenance', 'Maintenance'),
  payment('payment', 'Payment'),
  meeting('meeting', 'Meeting'),
  other('other', 'Other');

  final String value;
  final String displayName;

  const EventType(this.value, this.displayName);

  static EventType fromString(String value) {
    return EventType.values.firstWhere(
      (type) => type.value == value,
      orElse: () => EventType.other,
    );
  }
}
