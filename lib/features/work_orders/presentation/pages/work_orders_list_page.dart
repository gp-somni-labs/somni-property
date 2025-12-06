import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/work_orders/domain/entities/work_order.dart';
import 'package:somni_property/features/work_orders/presentation/providers/work_order_provider.dart';
import 'package:somni_property/features/work_orders/presentation/widgets/work_order_card.dart';

/// Page displaying list of all work orders (maintenance requests)
class WorkOrdersListPage extends ConsumerStatefulWidget {
  const WorkOrdersListPage({super.key});

  @override
  ConsumerState<WorkOrdersListPage> createState() => _WorkOrdersListPageState();
}

class _WorkOrdersListPageState extends ConsumerState<WorkOrdersListPage> {
  WorkOrderStatus? _selectedStatus;
  WorkOrderPriority? _selectedPriority;
  bool _showUrgentOnly = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(workOrdersProvider.notifier).loadWorkOrders();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(workOrdersProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Maintenance'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(workOrdersProvider.notifier).loadWorkOrders(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/maintenance/new'),
        icon: const Icon(Icons.add),
        label: const Text('New Request'),
      ),
      body: Column(
        children: [
          // Stats Cards
          if (state.stats != null)
            SizedBox(
              height: 120,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.all(16),
                children: [
                  SizedBox(
                    width: 140,
                    child: WorkOrderStatsCard(
                      title: 'Open',
                      value: state.stats!.openWorkOrders.toString(),
                      icon: Icons.assignment,
                      color: Colors.blue,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: WorkOrderStatsCard(
                      title: 'In Progress',
                      value: state.stats!.inProgressWorkOrders.toString(),
                      icon: Icons.engineering,
                      color: Colors.purple,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: WorkOrderStatsCard(
                      title: 'Urgent',
                      value: state.stats!.urgentWorkOrders.toString(),
                      icon: Icons.priority_high,
                      color: Colors.red,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: WorkOrderStatsCard(
                      title: 'Completed',
                      value: state.stats!.completedWorkOrders.toString(),
                      icon: Icons.check_circle,
                      color: Colors.green,
                    ),
                  ),
                ],
              ),
            ),

          // Filters
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                Row(
                  children: [
                    // Status Filter
                    Expanded(
                      child: DropdownButtonFormField<WorkOrderStatus?>(
                        value: _selectedStatus,
                        decoration: InputDecoration(
                          labelText: 'Status',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 12,
                          ),
                        ),
                        items: [
                          const DropdownMenuItem(
                            value: null,
                            child: Text('All Statuses'),
                          ),
                          ...WorkOrderStatus.values.map((status) => DropdownMenuItem(
                                value: status,
                                child: Text(status.displayName),
                              )),
                        ],
                        onChanged: (status) {
                          setState(() {
                            _selectedStatus = status;
                            _showUrgentOnly = false;
                          });
                          if (status == null) {
                            ref.read(workOrdersProvider.notifier).loadWorkOrders();
                          } else {
                            ref.read(workOrdersProvider.notifier).filterByStatus(status);
                          }
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    // Priority Filter
                    Expanded(
                      child: DropdownButtonFormField<WorkOrderPriority?>(
                        value: _selectedPriority,
                        decoration: InputDecoration(
                          labelText: 'Priority',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 12,
                          ),
                        ),
                        items: [
                          const DropdownMenuItem(
                            value: null,
                            child: Text('All Priorities'),
                          ),
                          ...WorkOrderPriority.values.map((priority) => DropdownMenuItem(
                                value: priority,
                                child: Text(priority.displayName),
                              )),
                        ],
                        onChanged: (priority) {
                          setState(() {
                            _selectedPriority = priority;
                            _showUrgentOnly = false;
                          });
                          if (priority == null) {
                            ref.read(workOrdersProvider.notifier).loadWorkOrders();
                          } else {
                            ref.read(workOrdersProvider.notifier).filterByPriority(priority);
                          }
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    FilterChip(
                      label: const Text('Urgent Only'),
                      selected: _showUrgentOnly,
                      avatar: _showUrgentOnly
                          ? null
                          : const Icon(Icons.warning_amber, size: 18),
                      onSelected: (selected) {
                        setState(() {
                          _showUrgentOnly = selected;
                          _selectedStatus = null;
                          _selectedPriority = null;
                        });
                        if (selected) {
                          ref.read(workOrdersProvider.notifier).loadUrgentWorkOrders();
                        } else {
                          ref.read(workOrdersProvider.notifier).loadWorkOrders();
                        }
                      },
                    ),
                    const SizedBox(width: 8),
                    FilterChip(
                      label: const Text('Open'),
                      selected: false,
                      avatar: const Icon(Icons.assignment, size: 18),
                      onSelected: (selected) {
                        setState(() {
                          _showUrgentOnly = false;
                          _selectedStatus = null;
                          _selectedPriority = null;
                        });
                        if (selected) {
                          ref.read(workOrdersProvider.notifier).loadOpenWorkOrders();
                        } else {
                          ref.read(workOrdersProvider.notifier).loadWorkOrders();
                        }
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Work Orders List
          Expanded(
            child: _buildWorkOrdersList(state),
          ),
        ],
      ),
    );
  }

  Widget _buildWorkOrdersList(WorkOrdersState state) {
    if (state.isLoading && state.workOrders.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.workOrders.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Error loading work orders',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(state.error!),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => ref.read(workOrdersProvider.notifier).loadWorkOrders(),
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.workOrders.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.build_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text(
              'No work orders found',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text('Create your first maintenance request'),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => context.push('/maintenance/new'),
              icon: const Icon(Icons.add),
              label: const Text('New Request'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(workOrdersProvider.notifier).loadWorkOrders(),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: state.workOrders.length,
        itemBuilder: (context, index) {
          final workOrder = state.workOrders[index];
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: WorkOrderCard(
              workOrder: workOrder,
              onTap: () => context.push('/maintenance/${workOrder.id}'),
              onStartWork: workOrder.status == WorkOrderStatus.open
                  ? () => _startWork(workOrder)
                  : null,
              onComplete: workOrder.status == WorkOrderStatus.inProgress
                  ? () => _showCompleteDialog(workOrder)
                  : null,
            ),
          );
        },
      ),
    );
  }

  Future<void> _startWork(WorkOrder workOrder) async {
    final success = await ref.read(workOrdersProvider.notifier).updateStatus(
          workOrder.id,
          WorkOrderStatus.inProgress,
        );
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(success ? 'Work started' : 'Failed to update status'),
          backgroundColor: success ? Colors.green : Colors.red,
        ),
      );
    }
  }

  Future<void> _showCompleteDialog(WorkOrder workOrder) async {
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

    if (confirmed == true && mounted) {
      final success = await ref.read(workOrdersProvider.notifier).completeWorkOrder(
            workOrder.id,
            DateTime.now(),
            double.tryParse(costController.text),
            notesController.text.isNotEmpty ? notesController.text : null,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(success
                ? 'Work order completed successfully'
                : 'Failed to complete work order'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    }
  }
}
