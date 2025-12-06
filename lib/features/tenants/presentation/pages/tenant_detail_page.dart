import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/tenants/domain/entities/tenant.dart';
import 'package:somni_property/features/tenants/presentation/providers/tenant_provider.dart';

/// Page displaying detailed tenant information
class TenantDetailPage extends ConsumerWidget {
  final String tenantId;

  const TenantDetailPage({super.key, required this.tenantId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(tenantDetailProvider(tenantId));
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    if (state.isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Tenant Details')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (state.error != null || state.tenant == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Tenant Details')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 64, color: colorScheme.error),
              const SizedBox(height: 16),
              Text(state.error ?? 'Tenant not found'),
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

    final tenant = state.tenant!;

    return Scaffold(
      appBar: AppBar(
        title: Text(tenant.fullName),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () => context.push('/tenants/${tenant.id}/edit'),
          ),
          PopupMenuButton<String>(
            onSelected: (value) async {
              if (value == 'delete') {
                final confirmed = await _showDeleteDialog(context, tenant);
                if (confirmed == true && context.mounted) {
                  final success = await ref
                      .read(tenantsProvider.notifier)
                      .deleteTenant(tenant.id);
                  if (context.mounted) {
                    if (success) {
                      context.pop();
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Failed to delete tenant'),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  }
                }
              }
            },
            itemBuilder: (context) => [
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
            ref.read(tenantDetailProvider(tenantId).notifier).refresh(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Profile Header
              _ProfileHeader(tenant: tenant),
              const SizedBox(height: 24),

              // Contact Information
              _SectionCard(
                title: 'Contact Information',
                icon: Icons.contact_phone,
                children: [
                  _InfoRow(
                    icon: Icons.email_outlined,
                    label: 'Email',
                    value: tenant.email,
                  ),
                  _InfoRow(
                    icon: Icons.phone_outlined,
                    label: 'Phone',
                    value: tenant.formattedPhone,
                  ),
                  if (tenant.dateOfBirth != null)
                    _InfoRow(
                      icon: Icons.cake_outlined,
                      label: 'Date of Birth',
                      value: tenant.dateOfBirth!,
                    ),
                ],
              ),
              const SizedBox(height: 16),

              // Emergency Contact
              if (tenant.emergencyContact != null)
                _SectionCard(
                  title: 'Emergency Contact',
                  icon: Icons.emergency,
                  children: [
                    _InfoRow(
                      icon: Icons.person_outlined,
                      label: 'Name',
                      value: tenant.emergencyContact!.name,
                    ),
                    _InfoRow(
                      icon: Icons.phone_outlined,
                      label: 'Phone',
                      value: tenant.emergencyContact!.phone,
                    ),
                    _InfoRow(
                      icon: Icons.people_outlined,
                      label: 'Relationship',
                      value: tenant.emergencyContact!.relationship,
                    ),
                  ],
                ),
              if (tenant.emergencyContact != null) const SizedBox(height: 16),

              // Lease Information
              _SectionCard(
                title: 'Lease Information',
                icon: Icons.description,
                children: [
                  _InfoRow(
                    icon: Icons.home_outlined,
                    label: 'Current Unit',
                    value: tenant.currentUnitId ?? 'No unit assigned',
                  ),
                  _InfoRow(
                    icon: Icons.assignment_outlined,
                    label: 'Current Lease',
                    value: tenant.currentLeaseId ?? 'No active lease',
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Notes
              if (tenant.notes != null && tenant.notes!.isNotEmpty)
                _SectionCard(
                  title: 'Notes',
                  icon: Icons.notes,
                  children: [
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Text(tenant.notes!),
                    ),
                  ],
                ),
              if (tenant.notes != null && tenant.notes!.isNotEmpty)
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
                        avatar: const Icon(Icons.email, size: 18),
                        label: const Text('Send Email'),
                        onPressed: () {
                          // TODO: Implement email
                        },
                      ),
                      ActionChip(
                        avatar: const Icon(Icons.phone, size: 18),
                        label: const Text('Call'),
                        onPressed: () {
                          // TODO: Implement call
                        },
                      ),
                      ActionChip(
                        avatar: const Icon(Icons.receipt_long, size: 18),
                        label: const Text('View Payments'),
                        onPressed: () {
                          // TODO: Navigate to payments
                        },
                      ),
                      ActionChip(
                        avatar: const Icon(Icons.build, size: 18),
                        label: const Text('Work Orders'),
                        onPressed: () {
                          // TODO: Navigate to work orders
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
                        'Created: ${_formatDate(tenant.createdAt)}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                      Text(
                        'Updated: ${_formatDate(tenant.updatedAt)}',
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

  Future<bool?> _showDeleteDialog(BuildContext context, Tenant tenant) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Tenant'),
        content: Text(
          'Are you sure you want to delete ${tenant.fullName}? This action cannot be undone.',
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

/// Profile header with avatar and status
class _ProfileHeader extends StatelessWidget {
  final Tenant tenant;

  const _ProfileHeader({required this.tenant});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          children: [
            CircleAvatar(
              radius: 48,
              backgroundColor: colorScheme.primaryContainer,
              backgroundImage: tenant.profileImageUrl != null
                  ? NetworkImage(tenant.profileImageUrl!)
                  : null,
              child: tenant.profileImageUrl == null
                  ? Text(
                      tenant.initials,
                      style: TextStyle(
                        color: colorScheme.onPrimaryContainer,
                        fontWeight: FontWeight.bold,
                        fontSize: 32,
                      ),
                    )
                  : null,
            ),
            const SizedBox(width: 24),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    tenant.fullName,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  _StatusBadge(status: tenant.status),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Status badge
class _StatusBadge extends StatelessWidget {
  final TenantStatus status;

  const _StatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    Color backgroundColor;
    Color textColor;

    switch (status) {
      case TenantStatus.active:
        backgroundColor = Colors.green.shade100;
        textColor = Colors.green.shade800;
        break;
      case TenantStatus.pending:
        backgroundColor = Colors.orange.shade100;
        textColor = Colors.orange.shade800;
        break;
      case TenantStatus.inactive:
        backgroundColor = Colors.grey.shade200;
        textColor = Colors.grey.shade700;
        break;
      case TenantStatus.evicted:
        backgroundColor = Colors.red.shade100;
        textColor = Colors.red.shade800;
        break;
      case TenantStatus.movedOut:
        backgroundColor = Colors.blue.shade100;
        textColor = Colors.blue.shade800;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        status.displayName,
        style: TextStyle(
          color: textColor,
          fontWeight: FontWeight.w600,
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
              style: theme.textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}
