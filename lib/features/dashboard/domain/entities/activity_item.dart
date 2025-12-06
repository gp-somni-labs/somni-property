import 'package:equatable/equatable.dart';

/// Activity item entity for the activity feed
class ActivityItem extends Equatable {
  final String id;
  final String title;
  final String description;
  final ActivityType type;
  final DateTime timestamp;
  final String? userId;
  final String? userName;
  final String? relatedEntityId;
  final String? relatedEntityType;
  final Map<String, dynamic>? metadata;

  const ActivityItem({
    required this.id,
    required this.title,
    required this.description,
    required this.type,
    required this.timestamp,
    this.userId,
    this.userName,
    this.relatedEntityId,
    this.relatedEntityType,
    this.metadata,
  });

  /// Get time ago string (e.g., "2 hours ago")
  String get timeAgo {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inDays > 7) {
      return '${difference.inDays ~/ 7} ${difference.inDays ~/ 7 == 1 ? 'week' : 'weeks'} ago';
    } else if (difference.inDays > 0) {
      return '${difference.inDays} ${difference.inDays == 1 ? 'day' : 'days'} ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours} ${difference.inHours == 1 ? 'hour' : 'hours'} ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes} ${difference.inMinutes == 1 ? 'minute' : 'minutes'} ago';
    } else {
      return 'Just now';
    }
  }

  /// Get date group (Today, Yesterday, This Week)
  String get dateGroup {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final itemDate = DateTime(timestamp.year, timestamp.month, timestamp.day);
    final difference = today.difference(itemDate).inDays;

    if (difference == 0) {
      return 'Today';
    } else if (difference == 1) {
      return 'Yesterday';
    } else if (difference <= 7) {
      return 'This Week';
    } else {
      return 'Earlier';
    }
  }

  @override
  List<Object?> get props => [
        id,
        title,
        description,
        type,
        timestamp,
        userId,
        userName,
        relatedEntityId,
        relatedEntityType,
        metadata,
      ];
}

/// Types of activities
enum ActivityType {
  propertyCreated('property_created', 'Property Created'),
  propertyUpdated('property_updated', 'Property Updated'),
  tenantAdded('tenant_added', 'Tenant Added'),
  tenantRemoved('tenant_removed', 'Tenant Removed'),
  leaseCreated('lease_created', 'Lease Created'),
  leaseExpiring('lease_expiring', 'Lease Expiring'),
  leaseRenewed('lease_renewed', 'Lease Renewed'),
  paymentReceived('payment_received', 'Payment Received'),
  paymentOverdue('payment_overdue', 'Payment Overdue'),
  workOrderCreated('work_order_created', 'Work Order Created'),
  workOrderCompleted('work_order_completed', 'Work Order Completed'),
  maintenanceScheduled('maintenance_scheduled', 'Maintenance Scheduled'),
  documentUploaded('document_uploaded', 'Document Uploaded'),
  userActivity('user_activity', 'User Activity'),
  systemAlert('system_alert', 'System Alert');

  final String value;
  final String displayName;

  const ActivityType(this.value, this.displayName);

  static ActivityType fromString(String value) {
    return ActivityType.values.firstWhere(
      (type) => type.value == value,
      orElse: () => ActivityType.userActivity,
    );
  }
}
