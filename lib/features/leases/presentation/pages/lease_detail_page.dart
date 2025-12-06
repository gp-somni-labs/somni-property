import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/leases/domain/entities/lease.dart';
import 'package:somni_property/features/leases/presentation/providers/lease_provider.dart';

/// Page displaying detailed lease information
class LeaseDetailPage extends ConsumerWidget {
  final String leaseId;

  const LeaseDetailPage({super.key, required this.leaseId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(leaseDetailProvider(leaseId));
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    if (state.isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Lease Details')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (state.error != null || state.lease == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Lease Details')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 64, color: colorScheme.error),
              const SizedBox(height: 16),
              Text(state.error ?? 'Lease not found'),
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

    final lease = state.lease!;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Lease Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () => context.push('/leases/${lease.id}/edit'),
          ),
          PopupMenuButton<String>(
            onSelected: (value) async {
              if (value == 'renew') {
                // TODO: Show renew dialog
              } else if (value == 'terminate') {
                // TODO: Show terminate dialog
              } else if (value == 'delete') {
                final confirmed = await _showDeleteDialog(context, lease);
                if (confirmed == true && context.mounted) {
                  final success = await ref
                      .read(leasesProvider.notifier)
                      .deleteLease(lease.id);
                  if (context.mounted) {
                    if (success) {
                      context.pop();
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Failed to delete lease'),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  }
                }
              }
            },
            itemBuilder: (context) => [
              if (lease.isActive)
                const PopupMenuItem(
                  value: 'renew',
                  child: Row(
                    children: [
                      Icon(Icons.autorenew),
                      SizedBox(width: 8),
                      Text('Renew'),
                    ],
                  ),
                ),
              if (lease.isActive)
                PopupMenuItem(
                  value: 'terminate',
                  child: Row(
                    children: [
                      Icon(Icons.cancel, color: colorScheme.error),
                      const SizedBox(width: 8),
                      Text('Terminate', style: TextStyle(color: colorScheme.error)),
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
            ref.read(leaseDetailProvider(leaseId).notifier).refresh(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Status Header
              _StatusHeader(lease: lease),
              const SizedBox(height: 24),

              // Lease Terms
              _SectionCard(
                title: 'Lease Terms',
                icon: Icons.description,
                children: [
                  _InfoRow(
                    icon: Icons.calendar_today,
                    label: 'Start Date',
                    value: _formatDate(lease.startDate),
                  ),
                  _InfoRow(
                    icon: Icons.event,
                    label: 'End Date',
                    value: _formatDate(lease.endDate),
                  ),
                  _InfoRow(
                    icon: Icons.timelapse,
                    label: 'Duration',
                    value: '${lease.durationMonths} months',
                  ),
                  if (lease.isActive)
                    _InfoRow(
                      icon: Icons.hourglass_bottom,
                      label: 'Days Remaining',
                      value: '${lease.daysUntilExpiry} days',
                    ),
                ],
              ),
              const SizedBox(height: 16),

              // Financial Details
              _SectionCard(
                title: 'Financial Details',
                icon: Icons.attach_money,
                children: [
                  _InfoRow(
                    icon: Icons.payments,
                    label: 'Monthly Rent',
                    value: '\$${lease.monthlyRent.toStringAsFixed(2)}',
                  ),
                  _InfoRow(
                    icon: Icons.security,
                    label: 'Security Deposit',
                    value: '\$${lease.securityDeposit.toStringAsFixed(2)}',
                  ),
                  _InfoRow(
                    icon: Icons.calculate,
                    label: 'Total Lease Value',
                    value: '\$${lease.totalValue.toStringAsFixed(2)}',
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Unit & Tenant
              _SectionCard(
                title: 'Unit & Tenant',
                icon: Icons.home,
                children: [
                  _InfoRow(
                    icon: Icons.apartment,
                    label: 'Unit',
                    value: lease.unitNumber ?? 'Unit #${lease.unitId}',
                  ),
                  _InfoRow(
                    icon: Icons.person,
                    label: 'Tenant',
                    value: lease.tenantName ?? 'Tenant #${lease.tenantId}',
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Special Conditions
              if (lease.specialConditions != null &&
                  lease.specialConditions!.isNotEmpty)
                _SectionCard(
                  title: 'Special Conditions',
                  icon: Icons.list_alt,
                  children: [
                    ...lease.specialConditions!.map(
                      (condition) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.check_circle,
                                size: 16, color: Colors.green),
                            const SizedBox(width: 8),
                            Expanded(child: Text(condition)),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              if (lease.specialConditions != null &&
                  lease.specialConditions!.isNotEmpty)
                const SizedBox(height: 16),

              // Terms & Notes
              if (lease.terms != null && lease.terms!.isNotEmpty)
                _SectionCard(
                  title: 'Terms',
                  icon: Icons.gavel,
                  children: [
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Text(lease.terms!),
                    ),
                  ],
                ),
              if (lease.terms != null && lease.terms!.isNotEmpty)
                const SizedBox(height: 16),

              if (lease.notes != null && lease.notes!.isNotEmpty)
                _SectionCard(
                  title: 'Notes',
                  icon: Icons.notes,
                  children: [
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Text(lease.notes!),
                    ),
                  ],
                ),
              if (lease.notes != null && lease.notes!.isNotEmpty)
                const SizedBox(height: 16),

              // Quick Actions
              _SectionCard(
                title: 'Quick Actions',
                icon: Icons.flash_on,
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      ActionChip(
                        avatar: const Icon(Icons.receipt_long, size: 18),
                        label: const Text('View Payments'),
                        onPressed: () {
                          // TODO: Navigate to payments filtered by lease
                        },
                      ),
                      ActionChip(
                        avatar: const Icon(Icons.folder, size: 18),
                        label: const Text('Documents'),
                        onPressed: () {
                          // TODO: Navigate to documents
                        },
                      ),
                      ActionChip(
                        avatar: const Icon(Icons.print, size: 18),
                        label: const Text('Print Lease'),
                        onPressed: () {
                          // TODO: Generate PDF
                        },
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Metadata
              Card(
                color: colorScheme.surfaceContainerLow,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Created: ${_formatDate(lease.createdAt)}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                      Text(
                        'Updated: ${_formatDate(lease.updatedAt)}',
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

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year}';
  }

  Future<bool?> _showDeleteDialog(BuildContext context, Lease lease) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Lease'),
        content: const Text(
          'Are you sure you want to delete this lease? This action cannot be undone.',
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
}

/// Status header with visual indicator
class _StatusHeader extends StatelessWidget {
  final Lease lease;

  const _StatusHeader({required this.lease});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    Color statusColor;
    IconData statusIcon;

    switch (lease.status) {
      case LeaseStatus.active:
        statusColor = Colors.green;
        statusIcon = Icons.check_circle;
        break;
      case LeaseStatus.pending:
        statusColor = Colors.orange;
        statusIcon = Icons.pending;
        break;
      case LeaseStatus.expired:
        statusColor = Colors.grey;
        statusIcon = Icons.event_busy;
        break;
      case LeaseStatus.terminated:
        statusColor = Colors.red;
        statusIcon = Icons.cancel;
        break;
      case LeaseStatus.renewed:
        statusColor = Colors.blue;
        statusIcon = Icons.autorenew;
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
                    lease.status.displayName,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: statusColor,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    lease.dateRangeFormatted,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  if (lease.isExpiringSoon) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.orange.shade100,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'Expires in ${lease.daysUntilExpiry} days',
                        style: TextStyle(
                          color: Colors.orange.shade800,
                          fontWeight: FontWeight.w500,
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

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
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
            width: 120,
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
              ),
            ),
          ),
        ],
      ),
    );
  }
}
