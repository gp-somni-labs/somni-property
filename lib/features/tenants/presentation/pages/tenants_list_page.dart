import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/tenants/domain/entities/tenant.dart';
import 'package:somni_property/features/tenants/presentation/providers/tenant_provider.dart';
import 'package:somni_property/features/tenants/presentation/widgets/tenant_card.dart';

/// Page displaying list of all tenants
class TenantsListPage extends ConsumerStatefulWidget {
  const TenantsListPage({super.key});

  @override
  ConsumerState<TenantsListPage> createState() => _TenantsListPageState();
}

class _TenantsListPageState extends ConsumerState<TenantsListPage> {
  final _searchController = TextEditingController();
  TenantStatus? _selectedStatus;

  @override
  void initState() {
    super.initState();
    // Load tenants when page opens
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(tenantsProvider.notifier).loadTenants();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(tenantsProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tenants'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(tenantsProvider.notifier).loadTenants(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/tenants/new'),
        icon: const Icon(Icons.add),
        label: const Text('Add Tenant'),
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
                    child: TenantStatsCard(
                      title: 'Total',
                      value: state.stats!.totalTenants.toString(),
                      icon: Icons.people,
                      color: colorScheme.primary,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: TenantStatsCard(
                      title: 'Active',
                      value: state.stats!.activeTenants.toString(),
                      icon: Icons.check_circle,
                      color: Colors.green,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: TenantStatsCard(
                      title: 'Pending',
                      value: state.stats!.pendingTenants.toString(),
                      icon: Icons.pending,
                      color: Colors.orange,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: TenantStatsCard(
                      title: 'Inactive',
                      value: state.stats!.inactiveTenants.toString(),
                      icon: Icons.pause_circle,
                      color: Colors.grey,
                    ),
                  ),
                ],
              ),
            ),

          // Search and Filter
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: 'Search tenants...',
                      prefixIcon: const Icon(Icons.search),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                      suffixIcon: _searchController.text.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear),
                              onPressed: () {
                                _searchController.clear();
                                ref.read(tenantsProvider.notifier).loadTenants();
                              },
                            )
                          : null,
                    ),
                    onSubmitted: (value) {
                      ref.read(tenantsProvider.notifier).searchTenants(value);
                    },
                  ),
                ),
                const SizedBox(width: 12),
                PopupMenuButton<TenantStatus?>(
                  icon: Badge(
                    isLabelVisible: _selectedStatus != null,
                    child: const Icon(Icons.filter_list),
                  ),
                  initialValue: _selectedStatus,
                  onSelected: (status) {
                    setState(() => _selectedStatus = status);
                    if (status == null) {
                      ref.read(tenantsProvider.notifier).loadTenants();
                    } else {
                      ref.read(tenantsProvider.notifier).filterByStatus(status);
                    }
                  },
                  itemBuilder: (context) => [
                    const PopupMenuItem(
                      value: null,
                      child: Text('All Statuses'),
                    ),
                    const PopupMenuDivider(),
                    ...TenantStatus.values.map(
                      (status) => PopupMenuItem(
                        value: status,
                        child: Text(status.displayName),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Tenant List
          Expanded(
            child: _buildTenantList(state),
          ),
        ],
      ),
    );
  }

  Widget _buildTenantList(TenantsState state) {
    if (state.isLoading && state.tenants.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.tenants.isEmpty) {
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
              'Error loading tenants',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              state.error!,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () =>
                  ref.read(tenantsProvider.notifier).loadTenants(),
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.tenants.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.people_outline,
              size: 64,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text(
              'No tenants found',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Add your first tenant to get started',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => context.push('/tenants/new'),
              icon: const Icon(Icons.add),
              label: const Text('Add Tenant'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(tenantsProvider.notifier).loadTenants(),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: state.tenants.length,
        itemBuilder: (context, index) {
          final tenant = state.tenants[index];
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: TenantCard(
              tenant: tenant,
              onTap: () => context.push('/tenants/${tenant.id}'),
              onEdit: () => context.push('/tenants/${tenant.id}/edit'),
              onDelete: () => _showDeleteDialog(tenant),
            ),
          );
        },
      ),
    );
  }

  Future<void> _showDeleteDialog(Tenant tenant) async {
    final confirmed = await showDialog<bool>(
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

    if (confirmed == true && mounted) {
      final success =
          await ref.read(tenantsProvider.notifier).deleteTenant(tenant.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(success
                ? 'Tenant deleted successfully'
                : 'Failed to delete tenant'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    }
  }
}
