import 'package:flutter/material.dart';
import 'package:somni_property/features/dashboard/domain/entities/alert.dart';

/// Alerts banner widget showing urgent notifications
class AlertsBanner extends StatelessWidget {
  final List<Alert> alerts;
  final Function(Alert)? onAlertTap;
  final Function(String)? onDismiss;

  const AlertsBanner({
    super.key,
    required this.alerts,
    this.onAlertTap,
    this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    if (alerts.isEmpty) {
      return const SizedBox.shrink();
    }

    // Show only critical and high priority alerts in banner
    final urgentAlerts = alerts
        .where((a) =>
            a.priority == AlertPriority.critical ||
            a.priority == AlertPriority.high)
        .take(3)
        .toList();

    if (urgentAlerts.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Urgent Alerts',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: Colors.red.shade700,
              ),
        ),
        const SizedBox(height: 12),
        ...urgentAlerts.map((alert) => _buildAlertCard(context, alert)),
      ],
    );
  }

  Widget _buildAlertCard(BuildContext context, Alert alert) {
    final color = _getAlertColor(alert.priority);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: color.withOpacity(0.1),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: color.withOpacity(0.3), width: 1),
      ),
      child: InkWell(
        onTap: () => onAlertTap?.call(alert),
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Icon
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _getAlertIcon(alert.type),
                  color: color,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),

              // Content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            alert.title,
                            style:
                                Theme.of(context).textTheme.bodyMedium?.copyWith(
                                      fontWeight: FontWeight.bold,
                                      color: color,
                                    ),
                          ),
                        ),
                        _buildPriorityBadge(context, alert.priority),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      alert.message,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurface
                                .withOpacity(0.8),
                          ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (alert.timeRemaining != null) ...[
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Icon(
                            Icons.schedule,
                            size: 12,
                            color: Theme.of(context)
                                .colorScheme
                                .onSurface
                                .withOpacity(0.6),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            alert.timeRemaining!,
                            style:
                                Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: Theme.of(context)
                                          .colorScheme
                                          .onSurface
                                          .withOpacity(0.6),
                                      fontSize: 11,
                                    ),
                          ),
                        ],
                      ),
                    ],
                    if (alert.actionLabel != null) ...[
                      const SizedBox(height: 8),
                      TextButton.icon(
                        onPressed: () => onAlertTap?.call(alert),
                        icon: const Icon(Icons.arrow_forward, size: 16),
                        label: Text(alert.actionLabel!),
                        style: TextButton.styleFrom(
                          foregroundColor: color,
                          padding: EdgeInsets.zero,
                          minimumSize: const Size(0, 32),
                        ),
                      ),
                    ],
                  ],
                ),
              ),

              // Dismiss button
              if (alert.isDismissible)
                IconButton(
                  icon: Icon(Icons.close, size: 18, color: color),
                  onPressed: () => onDismiss?.call(alert.id),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  visualDensity: VisualDensity.compact,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPriorityBadge(BuildContext context, AlertPriority priority) {
    final color = _getAlertColor(priority);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        priority.displayName.toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Color _getAlertColor(AlertPriority priority) {
    switch (priority) {
      case AlertPriority.critical:
        return Colors.red.shade700;
      case AlertPriority.high:
        return Colors.orange.shade700;
      case AlertPriority.medium:
        return Colors.amber.shade700;
      case AlertPriority.low:
        return Colors.blue.shade700;
    }
  }

  IconData _getAlertIcon(AlertType type) {
    switch (type) {
      case AlertType.leaseExpiring:
        return Icons.event_busy;
      case AlertType.paymentDue:
      case AlertType.paymentOverdue:
        return Icons.payment;
      case AlertType.maintenanceRequired:
      case AlertType.maintenanceScheduled:
        return Icons.build;
      case AlertType.workOrderCritical:
        return Icons.priority_high;
      case AlertType.documentExpiring:
        return Icons.description;
      case AlertType.inspectionDue:
        return Icons.assignment;
      case AlertType.complianceIssue:
        return Icons.gavel;
      case AlertType.systemNotification:
        return Icons.notifications;
    }
  }
}

/// Full alerts list widget
class AlertsList extends StatelessWidget {
  final List<Alert> alerts;
  final Function(Alert)? onAlertTap;
  final Function(String)? onDismiss;

  const AlertsList({
    super.key,
    required this.alerts,
    this.onAlertTap,
    this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    if (alerts.isEmpty) {
      return _buildEmptyState(context);
    }

    // Group by priority
    final grouped = <AlertPriority, List<Alert>>{};
    for (final alert in alerts) {
      if (!grouped.containsKey(alert.priority)) {
        grouped[alert.priority] = [];
      }
      grouped[alert.priority]!.add(alert);
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'All Alerts',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            if (grouped.containsKey(AlertPriority.critical))
              ...grouped[AlertPriority.critical]!.map(
                (alert) => AlertsBanner(
                  alerts: [alert],
                  onAlertTap: onAlertTap,
                  onDismiss: onDismiss,
                ),
              ),
            if (grouped.containsKey(AlertPriority.high))
              ...grouped[AlertPriority.high]!.map(
                (alert) => AlertsBanner(
                  alerts: [alert],
                  onAlertTap: onAlertTap,
                  onDismiss: onDismiss,
                ),
              ),
            if (grouped.containsKey(AlertPriority.medium))
              ...grouped[AlertPriority.medium]!.map(
                (alert) => AlertsBanner(
                  alerts: [alert],
                  onAlertTap: onAlertTap,
                  onDismiss: onDismiss,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.check_circle_outline,
                size: 48,
                color: Colors.green.shade300,
              ),
              const SizedBox(height: 16),
              Text(
                'No alerts',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color:
                          Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                'Everything looks good!',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color:
                          Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
