import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';
import 'package:somni_property/features/contractors/presentation/providers/contractor_provider.dart';
import 'package:somni_property/features/contractors/presentation/widgets/contractor_card.dart';
import 'package:somni_property/features/contractors/presentation/widgets/contractor_stats_card.dart';

/// Contractors list page with filtering and search
class ContractorsListScreen extends ConsumerStatefulWidget {
  const ContractorsListScreen({super.key});

  @override
  ConsumerState<ContractorsListScreen> createState() =>
      _ContractorsListScreenState();
}

class _ContractorsListScreenState extends ConsumerState<ContractorsListScreen> {
  final _searchController = TextEditingController();
  ContractorStatus? _statusFilter;
  String? _specialtyFilter;
  bool _showAvailableOnly = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(
        () => ref.read(contractorsProvider.notifier).loadContractors());
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final contractorsState = ref.watch(contractorsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Contractors'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
            tooltip: 'Filters',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () =>
            ref.read(contractorsProvider.notifier).loadContractors(),
        child: CustomScrollView(
          slivers: [
            // Stats cards at top
            if (contractorsState.stats != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: ContractorStatsCard(stats: contractorsState.stats!),
                ),
              ),

            // Search bar
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: _buildSearchBar(),
              ),
            ),

            // Filter chips
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: _buildFilterChips(),
              ),
            ),

            // Loading indicator
            if (contractorsState.isLoading)
              const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: CircularProgressIndicator()),
                ),
              ),

            // Error message
            if (contractorsState.error != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: _buildErrorCard(contractorsState.error!),
                ),
              ),

            // Contractors list
            if (!contractorsState.isLoading && contractorsState.error == null)
              _filteredContractors(contractorsState.contractors).isEmpty
                  ? SliverToBoxAdapter(child: _buildEmptyState())
                  : SliverPadding(
                      padding: const EdgeInsets.all(16),
                      sliver: SliverList(
                        delegate: SliverChildBuilderDelegate(
                          (context, index) {
                            final contractor =
                                _filteredContractors(
                                    contractorsState.contractors)[index];
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: ContractorCard(
                                contractor: contractor,
                                onTap: () => context.go(
                                    '/contractors/${contractor.id}'),
                              ),
                            );
                          },
                          childCount: _filteredContractors(
                                  contractorsState.contractors)
                              .length,
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
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.go('/contractors/new'),
        icon: const Icon(Icons.add),
        label: const Text('Add Contractor'),
      ),
    );
  }

  Widget _buildSearchBar() {
    return TextField(
      controller: _searchController,
      decoration: InputDecoration(
        hintText: 'Search contractors...',
        prefixIcon: const Icon(Icons.search),
        suffixIcon: _searchController.text.isNotEmpty
            ? IconButton(
                icon: const Icon(Icons.clear),
                onPressed: () {
                  _searchController.clear();
                  setState(() {});
                },
              )
            : null,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        filled: true,
      ),
      onChanged: (value) {
        setState(() {});
      },
    );
  }

  Widget _buildFilterChips() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          if (_statusFilter != null)
            Chip(
              label: Text(_statusFilter!.displayName),
              onDeleted: () {
                setState(() => _statusFilter = null);
              },
              deleteIcon: const Icon(Icons.close, size: 18),
            ),
          if (_statusFilter != null) const SizedBox(width: 8),
          if (_specialtyFilter != null)
            Chip(
              label: Text('Specialty: $_specialtyFilter'),
              onDeleted: () {
                setState(() => _specialtyFilter = null);
              },
              deleteIcon: const Icon(Icons.close, size: 18),
            ),
          if (_specialtyFilter != null) const SizedBox(width: 8),
          if (_showAvailableOnly)
            Chip(
              label: const Text('Available Only'),
              onDeleted: () {
                setState(() => _showAvailableOnly = false);
              },
              deleteIcon: const Icon(Icons.close, size: 18),
            ),
        ],
      ),
    );
  }

  Widget _buildErrorCard(String error) {
    return Card(
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
                error,
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onErrorContainer,
                ),
              ),
            ),
            TextButton(
              onPressed: () =>
                  ref.read(contractorsProvider.notifier).loadContractors(),
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.engineering_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
            ),
            const SizedBox(height: 16),
            Text(
              'No contractors found',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              _searchController.text.isNotEmpty || _statusFilter != null
                  ? 'Try adjusting your filters'
                  : 'Add your first contractor to get started',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () => context.go('/contractors/new'),
              icon: const Icon(Icons.add),
              label: const Text('Add Contractor'),
            ),
          ],
        ),
      ),
    );
  }

  List<Contractor> _filteredContractors(List<Contractor> contractors) {
    var filtered = contractors;

    // Search filter
    if (_searchController.text.isNotEmpty) {
      final query = _searchController.text.toLowerCase();
      filtered = filtered.where((c) {
        return c.fullName.toLowerCase().contains(query) ||
            c.company.toLowerCase().contains(query) ||
            c.specialty.toLowerCase().contains(query);
      }).toList();
    }

    // Status filter
    if (_statusFilter != null) {
      filtered = filtered.where((c) => c.status == _statusFilter).toList();
    }

    // Specialty filter
    if (_specialtyFilter != null) {
      filtered = filtered
          .where((c) => c.specialty.toLowerCase() == _specialtyFilter!.toLowerCase())
          .toList();
    }

    // Available only filter
    if (_showAvailableOnly) {
      filtered = filtered.where((c) => c.isAvailable).toList();
    }

    return filtered;
  }

  void _showFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Filter Contractors'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Status filter
              Text(
                'Status',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  ChoiceChip(
                    label: const Text('All'),
                    selected: _statusFilter == null,
                    onSelected: (selected) {
                      if (selected) {
                        setState(() => _statusFilter = null);
                        Navigator.pop(context);
                      }
                    },
                  ),
                  ...ContractorStatus.values.map((status) {
                    return ChoiceChip(
                      label: Text(status.displayName),
                      selected: _statusFilter == status,
                      onSelected: (selected) {
                        if (selected) {
                          setState(() => _statusFilter = status);
                          Navigator.pop(context);
                        }
                      },
                    );
                  }),
                ],
              ),
              const SizedBox(height: 16),

              // Available only
              CheckboxListTile(
                title: const Text('Available Only'),
                value: _showAvailableOnly,
                onChanged: (value) {
                  setState(() => _showAvailableOnly = value ?? false);
                  Navigator.pop(context);
                },
                contentPadding: EdgeInsets.zero,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              setState(() {
                _statusFilter = null;
                _specialtyFilter = null;
                _showAvailableOnly = false;
              });
              Navigator.pop(context);
            },
            child: const Text('Clear All'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }
}
