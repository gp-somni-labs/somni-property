import 'package:flutter/material.dart';
import 'package:somni_property/features/work_orders/domain/entities/work_order.dart';

/// Card widget displaying work order summary information
class WorkOrderCard extends StatelessWidget {
  final WorkOrder workOrder;
  final VoidCallback? onTap;
  final VoidCallback? onStartWork;
  final VoidCallback? onComplete;

  const WorkOrderCard({
    super.key,
    required this.workOrder,
    this.onTap,
    this.onStartWork,
    this.onComplete,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: _getCategoryColor(workOrder.category).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(
                      _getCategoryIcon(workOrder.category),
                      color: _getCategoryColor(workOrder.category),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          workOrder.title,
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          workOrder.category.displayName,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      _StatusChip(status: workOrder.status),
                      const SizedBox(height: 4),
                      _PriorityChip(priority: workOrder.priority),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Divider(height: 1),
              const SizedBox(height: 16),

              // Description
              Text(
                workOrder.description,
                style: theme.textTheme.bodySmall,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 12),

              // Details
              Row(
                children: [
                  if (workOrder.unitNumber != null)
                    Expanded(
                      child: _DetailItem(
                        icon: Icons.apartment,
                        label: 'Unit',
                        value: workOrder.unitNumber!,
                      ),
                    ),
                  Expanded(
                    child: _DetailItem(
                      icon: Icons.calendar_today,
                      label: 'Created',
                      value: workOrder.formattedCreatedDate,
                    ),
                  ),
                ],
              ),
              if (workOrder.assignedName != null || workOrder.scheduledDate != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    if (workOrder.assignedName != null)
                      Expanded(
                        child: _DetailItem(
                          icon: Icons.person,
                          label: 'Assigned',
                          value: workOrder.assignedName!,
                        ),
                      ),
                    if (workOrder.scheduledDate != null)
                      Expanded(
                        child: _DetailItem(
                          icon: Icons.event,
                          label: 'Scheduled',
                          value: workOrder.formattedScheduledDate!,
                        ),
                      ),
                  ],
                ),
              ],

              // Urgent warning
              if (workOrder.isUrgent) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.warning_amber,
                        color: Colors.red.shade700,
                        size: 18,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        workOrder.priority == WorkOrderPriority.emergency
                            ? 'Emergency - Immediate attention required!'
                            : 'Urgent - High priority',
                        style: TextStyle(
                          color: Colors.red.shade800,
                          fontWeight: FontWeight.w500,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              // Actions
              if ((onStartWork != null || onComplete != null) && workOrder.isOpen) ...[
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    if (onStartWork != null && workOrder.status == WorkOrderStatus.open)
                      TextButton.icon(
                        onPressed: onStartWork,
                        icon: const Icon(Icons.play_arrow, size: 18),
                        label: const Text('Start Work'),
                      ),
                    if (onComplete != null && workOrder.status == WorkOrderStatus.inProgress)
                      FilledButton.icon(
                        onPressed: onComplete,
                        icon: const Icon(Icons.check, size: 18),
                        label: const Text('Complete'),
                        style: FilledButton.styleFrom(
                          backgroundColor: Colors.green,
                        ),
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Color _getCategoryColor(WorkOrderCategory category) {
    switch (category) {
      case WorkOrderCategory.plumbing:
        return Colors.blue;
      case WorkOrderCategory.electrical:
        return Colors.amber;
      case WorkOrderCategory.hvac:
        return Colors.teal;
      case WorkOrderCategory.appliance:
        return Colors.purple;
      case WorkOrderCategory.structural:
        return Colors.brown;
      case WorkOrderCategory.pest:
        return Colors.orange;
      case WorkOrderCategory.cleaning:
        return Colors.cyan;
      case WorkOrderCategory.landscaping:
        return Colors.green;
      case WorkOrderCategory.security:
        return Colors.red;
      case WorkOrderCategory.general:
      case WorkOrderCategory.other:
        return Colors.grey;
    }
  }

  IconData _getCategoryIcon(WorkOrderCategory category) {
    switch (category) {
      case WorkOrderCategory.plumbing:
        return Icons.plumbing;
      case WorkOrderCategory.electrical:
        return Icons.electrical_services;
      case WorkOrderCategory.hvac:
        return Icons.ac_unit;
      case WorkOrderCategory.appliance:
        return Icons.kitchen;
      case WorkOrderCategory.structural:
        return Icons.foundation;
      case WorkOrderCategory.pest:
        return Icons.pest_control;
      case WorkOrderCategory.cleaning:
        return Icons.cleaning_services;
      case WorkOrderCategory.landscaping:
        return Icons.grass;
      case WorkOrderCategory.security:
        return Icons.security;
      case WorkOrderCategory.general:
      case WorkOrderCategory.other:
        return Icons.build;
    }
  }
}

/// Status indicator chip
class _StatusChip extends StatelessWidget {
  final WorkOrderStatus status;

  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    Color backgroundColor;
    Color textColor;

    switch (status) {
      case WorkOrderStatus.open:
        backgroundColor = Colors.blue.shade100;
        textColor = Colors.blue.shade800;
        break;
      case WorkOrderStatus.pending:
        backgroundColor = Colors.orange.shade100;
        textColor = Colors.orange.shade800;
        break;
      case WorkOrderStatus.inProgress:
        backgroundColor = Colors.purple.shade100;
        textColor = Colors.purple.shade800;
        break;
      case WorkOrderStatus.onHold:
        backgroundColor = Colors.amber.shade100;
        textColor = Colors.amber.shade800;
        break;
      case WorkOrderStatus.completed:
        backgroundColor = Colors.green.shade100;
        textColor = Colors.green.shade800;
        break;
      case WorkOrderStatus.cancelled:
        backgroundColor = Colors.grey.shade200;
        textColor = Colors.grey.shade700;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        status.displayName,
        style: TextStyle(
          color: textColor,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

/// Priority indicator chip
class _PriorityChip extends StatelessWidget {
  final WorkOrderPriority priority;

  const _PriorityChip({required this.priority});

  @override
  Widget build(BuildContext context) {
    Color color;

    switch (priority) {
      case WorkOrderPriority.low:
        color = Colors.green;
        break;
      case WorkOrderPriority.medium:
        color = Colors.blue;
        break;
      case WorkOrderPriority.high:
        color = Colors.orange;
        break;
      case WorkOrderPriority.urgent:
        color = Colors.red;
        break;
      case WorkOrderPriority.emergency:
        color = Colors.red.shade900;
        break;
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          priority == WorkOrderPriority.emergency
              ? Icons.emergency
              : priority == WorkOrderPriority.urgent
                  ? Icons.priority_high
                  : Icons.flag,
          size: 14,
          color: color,
        ),
        const SizedBox(width: 4),
        Text(
          priority.displayName,
          style: TextStyle(
            color: color,
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

/// Detail item widget
class _DetailItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _DetailItem({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Row(
      children: [
        Icon(icon, size: 16, color: colorScheme.outline),
        const SizedBox(width: 6),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
                fontSize: 11,
              ),
            ),
            Text(
              value,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Stats card for work order dashboard
class WorkOrderStatsCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color? color;

  const WorkOrderStatsCard({
    super.key,
    required this.title,
    required this.value,
    required this.icon,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final cardColor = color ?? colorScheme.primary;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: cardColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: cardColor, size: 20),
            ),
            const SizedBox(height: 12),
            Text(
              value,
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: cardColor,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
