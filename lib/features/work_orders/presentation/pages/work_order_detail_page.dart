import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/work_orders/domain/entities/work_order.dart';
import 'package:somni_property/features/work_orders/presentation/providers/work_order_provider.dart';

/// Page displaying detailed work order information
class WorkOrderDetailPage extends ConsumerWidget {
  final String workOrderId;

  const WorkOrderDetailPage({super.key, required this.workOrderId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(workOrderDetailProvider(workOrderId));
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    if (state.isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Work Order')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (state.error != null || state.workOrder == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Work Order')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 64, color: colorScheme.error),
              const SizedBox(height: 16),
              Text(state.error ?? 'Work order not found'),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: () => context.pop(),
                icon: const Icon(Icons.arrow_back),
                label: const Text('Go Back'),
              ),
            ],
          ),
        ),
      );
    }

    final workOrder = state.workOrder!;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Work Order'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () => context.push('/maintenance/${workOrder.id}/edit'),
          ),
          PopupMenuButton<String>(
            onSelected: (value) async {
              if (value == 'start' && workOrder.status == WorkOrderStatus.open) {
                _updateStatus(context, ref, workOrder, WorkOrderStatus.inProgress);
              } else if (value == 'hold') {
                _updateStatus(context, ref, workOrder, WorkOrderStatus.onHold);
              } else if (value == 'complete') {
                _showCompleteDialog(context, ref, workOrder);
              } else if (value == 'cancel') {
                _showCancelDialog(context, ref, workOrder);
              } else if (value == 'delete') {
                final confirmed = await _showDeleteDialog(context, workOrder);
                if (confirmed == true && context.mounted) {
                  final success = await ref
                      .read(workOrdersProvider.notifier)
                      .deleteWorkOrder(workOrder.id);
                  if (context.mounted) {
                    if (success) {
                      context.pop();
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Failed to delete work order'),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  }
                }
              }
            },
            itemBuilder: (context) => [
              if (workOrder.status == WorkOrderStatus.open)
                const PopupMenuItem(
                  value: 'start',
                  child: Row(
                    children: [
                      Icon(Icons.play_arrow, color: Colors.green),
                      SizedBox(width: 8),
                      Text('Start Work'),
                    ],
                  ),
                ),
              if (workOrder.isOpen && workOrder.status != WorkOrderStatus.onHold)
                const PopupMenuItem(
                  value: 'hold',
                  child: Row(
                    children: [
                      Icon(Icons.pause, color: Colors.amber),
                      SizedBox(width: 8),
                      Text('Put On Hold'),
                    ],
                  ),
                ),
              if (workOrder.status == WorkOrderStatus.inProgress)
                const PopupMenuItem(
                  value: 'complete',
                  child: Row(
                    children: [
                      Icon(Icons.check_circle, color: Colors.green),
                      SizedBox(width: 8),
                      Text('Mark Complete'),
                    ],
                  ),
                ),
              if (workOrder.isOpen)
                PopupMenuItem(
                  value: 'cancel',
                  child: Row(
                    children: [
                      Icon(Icons.cancel, color: colorScheme.error),
                      const SizedBox(width: 8),
                      Text('Cancel', style: TextStyle(color: colorScheme.error)),
                    ],
                  ),
                ),
              PopupMenuItem(
                value: 'delete',
                child: Row(
                  children: [
                    Icon(Icons.delete_outline, color: colorScheme.error),
                    const SizedBox(width: 8),
                    Text('Delete', style: TextStyle(color: colorScheme.error)),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () =>
            ref.read(workOrderDetailProvider(workOrderId).notifier).refresh(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Status Header
              _StatusHeader(workOrder: workOrder),
              const SizedBox(height: 24),

              // Title & Description
              _SectionCard(
                title: 'Details',
                icon: Icons.description,
                children: [
                  Text(
                    workOrder.title,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    workOrder.description,
                    style: theme.textTheme.bodyMedium,
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Category & Priority
              _SectionCard(
                title: 'Classification',
                icon: Icons.category,
                children: [
                  _InfoRow(
                    icon: Icons.build,
                    label: 'Category',
                    value: workOrder.category.displayName,
                  ),
                  _InfoRow(
                    icon: Icons.flag,
                    label: 'Priority',
                    value: workOrder.priority.displayName,
                    valueColor: _getPriorityColor(workOrder.priority),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Location & Assignment
              _SectionCard(
                title: 'Assignment',
                icon: Icons.location_on,
                children: [
                  _InfoRow(
                    icon: Icons.apartment,
                    label: 'Unit',
                    value: workOrder.unitNumber ?? 'Unit #${workOrder.unitId}',
                  ),
                  if (workOrder.tenantName != null)
                    _InfoRow(
                      icon: Icons.person,
                      label: 'Tenant',
                      value: workOrder.tenantName!,
                    ),
                  _InfoRow(
                    icon: Icons.engineering,
                    label: 'Assigned To',
                    value: workOrder.assignedName ?? 'Unassigned',
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Dates
              _SectionCard(
                title: 'Schedule',
                icon: Icons.calendar_today,
                children: [
                  _InfoRow(
                    icon: Icons.add_circle,
                    label: 'Created',
                    value: workOrder.formattedCreatedDate,
                  ),
                  if (workOrder.scheduledDate != null)
                    _InfoRow(
                      icon: Icons.event,
                      label: 'Scheduled',
                      value: workOrder.formattedScheduledDate!,
                    ),
                  if (workOrder.completedDate != null)
                    _InfoRow(
                      icon: Icons.check_circle,
                      label: 'Completed',
                      value: workOrder.formattedCompletedDate!,
                    ),
                ],
              ),
              const SizedBox(height: 16),

              // Costs
              if (workOrder.estimatedCost != null || workOrder.actualCost != null)
                _SectionCard(
                  title: 'Costs',
                  icon: Icons.attach_money,
                  children: [
                    if (workOrder.estimatedCost != null)
                      _InfoRow(
                        icon: Icons.calculate,
                        label: 'Estimated',
                        value: '\$${workOrder.estimatedCost!.toStringAsFixed(2)}',
                      ),
                    if (workOrder.actualCost != null)
                      _InfoRow(
                        icon: Icons.receipt,
                        label: 'Actual',
                        value: '\$${workOrder.actualCost!.toStringAsFixed(2)}',
                        valueColor: colorScheme.primary,
                      ),
                  ],
                ),
              if (workOrder.estimatedCost != null || workOrder.actualCost != null)
                const SizedBox(height: 16),

              // Notes
              if (workOrder.notes != null && workOrder.notes!.isNotEmpty)
                _SectionCard(
                  title: 'Notes',
                  icon: Icons.notes,
                  children: [
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Text(workOrder.notes!),
                    ),
                  ],
                ),
              if (workOrder.notes != null && workOrder.notes!.isNotEmpty)
                const SizedBox(height: 16),

              // Quick Actions
              if (workOrder.isOpen)
                _SectionCard(
                  title: 'Quick Actions',
                  icon: Icons.flash_on,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        if (workOrder.status == WorkOrderStatus.open)
                          FilledButton.icon(
                            onPressed: () => _updateStatus(
                                context, ref, workOrder, WorkOrderStatus.inProgress),
                            icon: const Icon(Icons.play_arrow, size: 18),
                            label: const Text('Start Work'),
                          ),
                        if (workOrder.status == WorkOrderStatus.inProgress)
                          FilledButton.icon(
                            onPressed: () =>
                                _showCompleteDialog(context, ref, workOrder),
                            icon: const Icon(Icons.check, size: 18),
                            label: const Text('Complete'),
                            style: FilledButton.styleFrom(
                              backgroundColor: Colors.green,
                            ),
                          ),
                        OutlinedButton.icon(
                          onPressed: () {
                            // TODO: Assign work order
                          },
                          icon: const Icon(Icons.person_add, size: 18),
                          label: const Text('Assign'),
                        ),
                      ],
                    ),
                  ],
                ),
              if (workOrder.isOpen) const SizedBox(height: 16),

              // Metadata
              Card(
                color: colorScheme.surfaceContainerLow,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Created: ${_formatDate(workOrder.createdAt)}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                      Text(
                        'Updated: ${_formatDate(workOrder.updatedAt)}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getPriorityColor(WorkOrderPriority priority) {
    switch (priority) {
      case WorkOrderPriority.low:
        return Colors.green;
      case WorkOrderPriority.medium:
        return Colors.blue;
      case WorkOrderPriority.high:
        return Colors.orange;
      case WorkOrderPriority.urgent:
        return Colors.red;
      case WorkOrderPriority.emergency:
        return Colors.red.shade900;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year}';
  }

  Future<bool?> _showDeleteDialog(BuildContext context, WorkOrder workOrder) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Work Order'),
        content: const Text(
          'Are you sure you want to delete this work order? This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  Future<void> _updateStatus(
    BuildContext context,
    WidgetRef ref,
    WorkOrder workOrder,
    WorkOrderStatus status,
  ) async {
    final success =
        await ref.read(workOrdersProvider.notifier).updateStatus(workOrder.id, status);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(success ? 'Status updated' : 'Failed to update status'),
          backgroundColor: success ? Colors.green : Colors.red,
        ),
      );
      if (success) {
        ref.read(workOrderDetailProvider(workOrderId).notifier).refresh();
      }
    }
  }

  Future<void> _showCompleteDialog(
    BuildContext context,
    WidgetRef ref,
    WorkOrder workOrder,
  ) async {
    final costController = TextEditingController();
    final notesController = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Complete Work Order'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: costController,
              decoration: const InputDecoration(
                labelText: 'Actual Cost',
                border: OutlineInputBorder(),
                prefixText: '\$',
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: notesController,
              decoration: const InputDecoration(
                labelText: 'Completion Notes',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(backgroundColor: Colors.green),
            child: const Text('Complete'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      final success = await ref.read(workOrdersProvider.notifier).completeWorkOrder(
            workOrder.id,
            DateTime.now(),
            double.tryParse(costController.text),
            notesController.text.isNotEmpty ? notesController.text : null,
          );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(success
                ? 'Work order completed'
                : 'Failed to complete work order'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
        if (success) {
          ref.read(workOrderDetailProvider(workOrderId).notifier).refresh();
        }
      }
    }
  }

  Future<void> _showCancelDialog(
    BuildContext context,
    WidgetRef ref,
    WorkOrder workOrder,
  ) async {
    final reasonController = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel Work Order'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Are you sure you want to cancel this work order?'),
            const SizedBox(height: 16),
            TextField(
              controller: reasonController,
              decoration: const InputDecoration(
                labelText: 'Reason *',
                border: OutlineInputBorder(),
              ),
              maxLines: 2,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('No'),
          ),
          FilledButton(
            onPressed: () {
              if (reasonController.text.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Please provide a reason'),
                    backgroundColor: Colors.red,
                  ),
                );
                return;
              }
              Navigator.of(context).pop(true);
            },
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Cancel Work Order'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      final success = await ref.read(workOrdersProvider.notifier).cancelWorkOrder(
            workOrder.id,
            reasonController.text,
          );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content:
                Text(success ? 'Work order cancelled' : 'Failed to cancel work order'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
        if (success) {
          ref.read(workOrderDetailProvider(workOrderId).notifier).refresh();
        }
      }
    }
  }
}

/// Status header with visual indicator
class _StatusHeader extends StatelessWidget {
  final WorkOrder workOrder;

  const _StatusHeader({required this.workOrder});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    Color statusColor;
    IconData statusIcon;

    switch (workOrder.status) {
      case WorkOrderStatus.open:
        statusColor = Colors.blue;
        statusIcon = Icons.assignment;
        break;
      case WorkOrderStatus.pending:
        statusColor = Colors.orange;
        statusIcon = Icons.pending;
        break;
      case WorkOrderStatus.inProgress:
        statusColor = Colors.purple;
        statusIcon = Icons.engineering;
        break;
      case WorkOrderStatus.onHold:
        statusColor = Colors.amber;
        statusIcon = Icons.pause_circle;
        break;
      case WorkOrderStatus.completed:
        statusColor = Colors.green;
        statusIcon = Icons.check_circle;
        break;
      case WorkOrderStatus.cancelled:
        statusColor = Colors.grey;
        statusIcon = Icons.cancel;
        break;
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Icon(statusIcon, color: statusColor, size: 40),
            ),
            const SizedBox(width: 24),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    workOrder.status.displayName,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: statusColor,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    workOrder.category.displayName,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  if (workOrder.isUrgent) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.red.shade100,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        workOrder.priority == WorkOrderPriority.emergency
                            ? 'EMERGENCY'
                            : 'URGENT',
                        style: TextStyle(
                          color: Colors.red.shade800,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Section card with title and icon
class _SectionCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Widget> children;

  const _SectionCard({
    required this.title,
    required this.icon,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: colorScheme.primary, size: 20),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            ...children,
          ],
        ),
      ),
    );
  }
}

/// Info row with icon, label and value
class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: colorScheme.outline),
          const SizedBox(width: 12),
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
                color: valueColor,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
