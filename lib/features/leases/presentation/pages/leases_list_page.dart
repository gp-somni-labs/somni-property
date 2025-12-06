import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/leases/domain/entities/lease.dart';
import 'package:somni_property/features/leases/presentation/providers/lease_provider.dart';
import 'package:somni_property/features/leases/presentation/widgets/lease_card.dart';

/// Page displaying list of all leases
class LeasesListPage extends ConsumerStatefulWidget {
  const LeasesListPage({super.key});

  @override
  ConsumerState<LeasesListPage> createState() => _LeasesListPageState();
}

class _LeasesListPageState extends ConsumerState<LeasesListPage> {
  LeaseStatus? _selectedStatus;
  bool _showExpiringOnly = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(leasesProvider.notifier).loadLeases();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(leasesProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Leases'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(leasesProvider.notifier).loadLeases(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/leases/new'),
        icon: const Icon(Icons.add),
        label: const Text('New Lease'),
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
                    child: LeaseStatsCard(
                      title: 'Total',
                      value: state.stats!.totalLeases.toString(),
                      icon: Icons.description,
                      color: colorScheme.primary,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: LeaseStatsCard(
                      title: 'Active',
                      value: state.stats!.activeLeases.toString(),
                      icon: Icons.check_circle,
                      color: Colors.green,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: LeaseStatsCard(
                      title: 'Expiring',
                      value: state.stats!.expiringLeases.toString(),
                      icon: Icons.warning,
                      color: Colors.orange,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 160,
                    child: LeaseStatsCard(
                      title: 'Monthly Rev',
                      value: '\$${state.stats!.totalMonthlyRevenue.toStringAsFixed(0)}',
                      icon: Icons.attach_money,
                      color: Colors.teal,
                    ),
                  ),
                ],
              ),
            ),

          // Filters
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                // Status Filter
                Expanded(
                  child: DropdownButtonFormField<LeaseStatus?>(
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
                      ...LeaseStatus.values.map((status) => DropdownMenuItem(
                            value: status,
                            child: Text(status.displayName),
                          )),
                    ],
                    onChanged: (status) {
                      setState(() {
                        _selectedStatus = status;
                        _showExpiringOnly = false;
                      });
                      if (status == null) {
                        ref.read(leasesProvider.notifier).loadLeases();
                      } else {
                        ref.read(leasesProvider.notifier).filterByStatus(status);
                      }
                    },
                  ),
                ),
                const SizedBox(width: 12),
                // Expiring Filter
                FilterChip(
                  label: const Text('Expiring Soon'),
                  selected: _showExpiringOnly,
                  onSelected: (selected) {
                    setState(() {
                      _showExpiringOnly = selected;
                      _selectedStatus = null;
                    });
                    if (selected) {
                      ref.read(leasesProvider.notifier).loadExpiringLeases();
                    } else {
                      ref.read(leasesProvider.notifier).loadLeases();
                    }
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Lease List
          Expanded(
            child: _buildLeaseList(state),
          ),
        ],
      ),
    );
  }

  Widget _buildLeaseList(LeasesState state) {
    if (state.isLoading && state.leases.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.leases.isEmpty) {
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
              'Error loading leases',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(state.error!),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => ref.read(leasesProvider.notifier).loadLeases(),
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.leases.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.description_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text(
              'No leases found',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text('Create your first lease to get started'),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => context.push('/leases/new'),
              icon: const Icon(Icons.add),
              label: const Text('New Lease'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(leasesProvider.notifier).loadLeases(),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: state.leases.length,
        itemBuilder: (context, index) {
          final lease = state.leases[index];
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: LeaseCard(
              lease: lease,
              onTap: () => context.push('/leases/${lease.id}'),
              onRenew: () => _showRenewDialog(lease),
              onTerminate: () => _showTerminateDialog(lease),
            ),
          );
        },
      ),
    );
  }

  Future<void> _showRenewDialog(Lease lease) async {
    DateTime newEndDate = lease.endDate.add(const Duration(days: 365));
    double? newRent;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Renew Lease'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Current end date: ${_formatDate(lease.endDate)}'),
            const SizedBox(height: 16),
            ListTile(
              title: const Text('New End Date'),
              subtitle: Text(_formatDate(newEndDate)),
              trailing: const Icon(Icons.calendar_today),
              onTap: () async {
                final date = await showDatePicker(
                  context: context,
                  initialDate: newEndDate,
                  firstDate: lease.endDate,
                  lastDate: lease.endDate.add(const Duration(days: 730)),
                );
                if (date != null) {
                  newEndDate = date;
                }
              },
            ),
            const SizedBox(height: 8),
            TextField(
              decoration: const InputDecoration(
                labelText: 'New Monthly Rent (optional)',
                border: OutlineInputBorder(),
                prefixText: '\$',
              ),
              keyboardType: TextInputType.number,
              onChanged: (value) {
                newRent = double.tryParse(value);
              },
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
            child: const Text('Renew'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final success = await ref
          .read(leasesProvider.notifier)
          .renewLease(lease.id, newEndDate, newRent);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                success ? 'Lease renewed successfully' : 'Failed to renew lease'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _showTerminateDialog(Lease lease) async {
    final reasonController = TextEditingController();
    DateTime terminationDate = DateTime.now();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Terminate Lease'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Are you sure you want to terminate this lease? This action cannot be undone.',
              style: TextStyle(color: Colors.red),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: reasonController,
              decoration: const InputDecoration(
                labelText: 'Reason for termination *',
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
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Terminate'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final success = await ref
          .read(leasesProvider.notifier)
          .terminateLease(lease.id, terminationDate, reasonController.text);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(success
                ? 'Lease terminated successfully'
                : 'Failed to terminate lease'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    }
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year}';
  }
}
