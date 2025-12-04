import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/auth/presentation/bloc/auth_provider.dart';
import 'package:somni_property/features/properties/domain/entities/property.dart';
import 'package:somni_property/features/properties/presentation/providers/property_provider.dart';
import 'package:somni_property/features/properties/presentation/widgets/property_card.dart';
import 'package:somni_property/features/properties/presentation/widgets/property_stats_card.dart';

/// Properties list page with filtering and search
class PropertiesListPage extends ConsumerStatefulWidget {
  const PropertiesListPage({super.key});

  @override
  ConsumerState<PropertiesListPage> createState() => _PropertiesListPageState();
}

class _PropertiesListPageState extends ConsumerState<PropertiesListPage> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final propertiesState = ref.watch(propertiesProvider);
    final currentUser = ref.watch(currentUserProvider);
    final canManage = currentUser?.role == 'admin' || currentUser?.role == 'manager';

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () => ref.read(propertiesProvider.notifier).loadProperties(),
        child: CustomScrollView(
          slivers: [
            // Stats cards at top
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: PropertyStatsCard(stats: propertiesState.stats),
              ),
            ),

            // Search and filter bar
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: _buildSearchAndFilters(propertiesState),
              ),
            ),

            // Loading indicator
            if (propertiesState.isLoading)
              const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: CircularProgressIndicator()),
                ),
              ),

            // Error message
            if (propertiesState.error != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Card(
                    color: Theme.of(context).colorScheme.errorContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          Icon(
                            Icons.error_outline,
                            color: Theme.of(context).colorScheme.error,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              propertiesState.error!,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.onErrorContainer,
                              ),
                            ),
                          ),
                          TextButton(
                            onPressed: () =>
                                ref.read(propertiesProvider.notifier).loadProperties(),
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

            // Properties list
            if (!propertiesState.isLoading && propertiesState.error == null)
              propertiesState.filteredProperties.isEmpty
                  ? SliverToBoxAdapter(
                      child: _buildEmptyState(propertiesState),
                    )
                  : SliverPadding(
                      padding: const EdgeInsets.all(16),
                      sliver: SliverGrid(
                        gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                          maxCrossAxisExtent: 400,
                          mainAxisSpacing: 16,
                          crossAxisSpacing: 16,
                          childAspectRatio: 1.1,
                        ),
                        delegate: SliverChildBuilderDelegate(
                          (context, index) {
                            final property =
                                propertiesState.filteredProperties[index];
                            return PropertyCard(
                              property: property,
                              onTap: () => context.go('/properties/${property.id}'),
                              onEdit: canManage
                                  ? () => context.go('/properties/${property.id}/edit')
                                  : null,
                              onDelete: canManage
                                  ? () => _confirmDelete(property)
                                  : null,
                            );
                          },
                          childCount: propertiesState.filteredProperties.length,
                        ),
                      ),
                    ),

            // Bottom padding
            const SliverToBoxAdapter(
              child: SizedBox(height: 80),
            ),
          ],
        ),
      ),
      floatingActionButton: canManage
          ? FloatingActionButton.extended(
              onPressed: () => context.go('/properties/new'),
              icon: const Icon(Icons.add),
              label: const Text('Add Property'),
            )
          : null,
    );
  }

  Widget _buildSearchAndFilters(PropertiesState state) {
    return Column(
      children: [
        // Search bar
        TextField(
          controller: _searchController,
          decoration: InputDecoration(
            hintText: 'Search properties...',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: _searchController.text.isNotEmpty
                ? IconButton(
                    icon: const Icon(Icons.clear),
                    onPressed: () {
                      _searchController.clear();
                      ref.read(propertiesProvider.notifier).setSearchQuery('');
                    },
                  )
                : null,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            filled: true,
          ),
          onChanged: (value) {
            ref.read(propertiesProvider.notifier).setSearchQuery(value);
          },
        ),
        const SizedBox(height: 12),

        // Filter chips
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              // Type filter
              FilterChip(
                label: Text(state.typeFilter?.displayName ?? 'All Types'),
                selected: state.typeFilter != null,
                onSelected: (_) => _showTypeFilterDialog(),
                avatar: const Icon(Icons.home_work, size: 18),
              ),
              const SizedBox(width: 8),

              // Status filter
              FilterChip(
                label: Text(state.statusFilter?.displayName ?? 'All Status'),
                selected: state.statusFilter != null,
                onSelected: (_) => _showStatusFilterDialog(),
                avatar: const Icon(Icons.flag, size: 18),
              ),
              const SizedBox(width: 8),

              // Clear filters
              if (state.typeFilter != null ||
                  state.statusFilter != null ||
                  state.searchQuery.isNotEmpty)
                ActionChip(
                  label: const Text('Clear Filters'),
                  onPressed: () {
                    _searchController.clear();
                    ref.read(propertiesProvider.notifier).clearFilters();
                  },
                  avatar: const Icon(Icons.clear_all, size: 18),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _buildEmptyState(PropertiesState state) {
    final hasFilters = state.typeFilter != null ||
        state.statusFilter != null ||
        state.searchQuery.isNotEmpty;

    return Padding(
      padding: const EdgeInsets.all(32),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              hasFilters ? Icons.filter_list_off : Icons.home_work_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text(
              hasFilters ? 'No properties match your filters' : 'No properties yet',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              hasFilters
                  ? 'Try adjusting your search or filters'
                  : 'Add your first property to get started',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.outline,
                  ),
            ),
            if (hasFilters) ...[
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: () {
                  _searchController.clear();
                  ref.read(propertiesProvider.notifier).clearFilters();
                },
                icon: const Icon(Icons.clear_all),
                label: const Text('Clear Filters'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _showTypeFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Filter by Type'),
        children: [
          SimpleDialogOption(
            onPressed: () {
              ref.read(propertiesProvider.notifier).setTypeFilter(null);
              Navigator.pop(context);
            },
            child: const Text('All Types'),
          ),
          ...PropertyType.values.map((type) => SimpleDialogOption(
                onPressed: () {
                  ref.read(propertiesProvider.notifier).setTypeFilter(type);
                  Navigator.pop(context);
                },
                child: Text(type.displayName),
              )),
        ],
      ),
    );
  }

  void _showStatusFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Filter by Status'),
        children: [
          SimpleDialogOption(
            onPressed: () {
              ref.read(propertiesProvider.notifier).setStatusFilter(null);
              Navigator.pop(context);
            },
            child: const Text('All Status'),
          ),
          ...PropertyStatus.values.map((status) => SimpleDialogOption(
                onPressed: () {
                  ref.read(propertiesProvider.notifier).setStatusFilter(status);
                  Navigator.pop(context);
                },
                child: Text(status.displayName),
              )),
        ],
      ),
    );
  }

  Future<void> _confirmDelete(Property property) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Property'),
        content: Text('Are you sure you want to delete "${property.name}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
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
          await ref.read(propertiesProvider.notifier).deleteProperty(property.id);
      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${property.name} deleted')),
        );
      }
    }
  }
}
