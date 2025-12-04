import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/auth/presentation/bloc/auth_provider.dart';
import 'package:somni_property/features/properties/domain/entities/property.dart';
import 'package:somni_property/features/properties/presentation/providers/property_provider.dart';

/// Property detail page showing full property information
class PropertyDetailPage extends ConsumerWidget {
  final String propertyId;

  const PropertyDetailPage({super.key, required this.propertyId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final propertyAsync = ref.watch(propertyByIdProvider(propertyId));
    final currentUser = ref.watch(currentUserProvider);
    final canManage = currentUser?.role == 'admin' || currentUser?.role == 'manager';

    return propertyAsync.when(
      loading: () => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (error, stack) => Scaffold(
        appBar: AppBar(title: const Text('Property')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 64, color: Colors.red),
              const SizedBox(height: 16),
              Text('Error: $error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => context.go('/properties'),
                child: const Text('Back to Properties'),
              ),
            ],
          ),
        ),
      ),
      data: (property) {
        if (property == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Property')),
            body: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.home_work_outlined, size: 64),
                  const SizedBox(height: 16),
                  const Text('Property not found'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () => context.go('/properties'),
                    child: const Text('Back to Properties'),
                  ),
                ],
              ),
            ),
          );
        }

        return _PropertyDetailContent(
          property: property,
          canManage: canManage,
        );
      },
    );
  }
}

class _PropertyDetailContent extends StatelessWidget {
  final Property property;
  final bool canManage;

  const _PropertyDetailContent({
    required this.property,
    required this.canManage,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          // App bar with property image/header
          SliverAppBar(
            expandedHeight: 200,
            pinned: true,
            flexibleSpace: FlexibleSpaceBar(
              title: Text(
                property.name,
                style: const TextStyle(
                  shadows: [Shadow(blurRadius: 4, color: Colors.black54)],
                ),
              ),
              background: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      colorScheme.primary,
                      colorScheme.primaryContainer,
                    ],
                  ),
                ),
                child: Center(
                  child: Icon(
                    _getTypeIcon(property.type),
                    size: 80,
                    color: colorScheme.onPrimary.withOpacity(0.5),
                  ),
                ),
              ),
            ),
            actions: [
              if (canManage)
                IconButton(
                  icon: const Icon(Icons.edit),
                  onPressed: () => context.go('/properties/${property.id}/edit'),
                  tooltip: 'Edit Property',
                ),
            ],
          ),

          // Content
          SliverPadding(
            padding: const EdgeInsets.all(16),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                // Status and type badges
                Wrap(
                  spacing: 8,
                  children: [
                    Chip(
                      avatar: Icon(
                        _getStatusIcon(property.status),
                        size: 18,
                        color: _getStatusColor(property.status),
                      ),
                      label: Text(property.status.displayName),
                    ),
                    Chip(
                      avatar: Icon(
                        _getTypeIcon(property.type),
                        size: 18,
                      ),
                      label: Text(property.type.displayName),
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                // Address section
                _SectionCard(
                  title: 'Location',
                  icon: Icons.location_on,
                  children: [
                    _InfoRow(label: 'Address', value: property.address),
                    _InfoRow(label: 'City', value: property.city),
                    _InfoRow(label: 'State', value: property.state),
                    _InfoRow(label: 'ZIP Code', value: property.zipCode),
                  ],
                ),
                const SizedBox(height: 16),

                // Units & occupancy section
                _SectionCard(
                  title: 'Units & Occupancy',
                  icon: Icons.door_front_door,
                  children: [
                    _InfoRow(
                      label: 'Total Units',
                      value: property.totalUnits.toString(),
                    ),
                    _InfoRow(
                      label: 'Occupied Units',
                      value: property.occupiedUnits.toString(),
                    ),
                    _InfoRow(
                      label: 'Available Units',
                      value: property.availableUnits.toString(),
                    ),
                    _InfoRow(
                      label: 'Occupancy Rate',
                      value: '${property.occupancyRate.toStringAsFixed(1)}%',
                      valueColor: _getOccupancyColor(property.occupancyRate),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Financial section
                if (property.monthlyRevenue != null)
                  _SectionCard(
                    title: 'Financial',
                    icon: Icons.attach_money,
                    children: [
                      _InfoRow(
                        label: 'Monthly Revenue',
                        value: '\$${property.monthlyRevenue!.toStringAsFixed(2)}',
                      ),
                      _InfoRow(
                        label: 'Annual Revenue (est.)',
                        value: '\$${(property.monthlyRevenue! * 12).toStringAsFixed(2)}',
                      ),
                    ],
                  ),
                if (property.monthlyRevenue != null) const SizedBox(height: 16),

                // Description section
                if (property.description != null && property.description!.isNotEmpty)
                  _SectionCard(
                    title: 'Description',
                    icon: Icons.description,
                    children: [
                      Text(
                        property.description!,
                        style: theme.textTheme.bodyMedium,
                      ),
                    ],
                  ),
                if (property.description != null && property.description!.isNotEmpty)
                  const SizedBox(height: 16),

                // Metadata section
                _SectionCard(
                  title: 'Details',
                  icon: Icons.info_outline,
                  children: [
                    _InfoRow(label: 'Property ID', value: property.id),
                    _InfoRow(label: 'Owner ID', value: property.ownerId),
                    if (property.managerId != null)
                      _InfoRow(label: 'Manager ID', value: property.managerId!),
                    _InfoRow(
                      label: 'Created',
                      value: _formatDate(property.createdAt),
                    ),
                    _InfoRow(
                      label: 'Last Updated',
                      value: _formatDate(property.updatedAt),
                    ),
                  ],
                ),
                const SizedBox(height: 80), // Bottom padding for FAB
              ]),
            ),
          ),
        ],
      ),
      floatingActionButton: canManage
          ? FloatingActionButton.extended(
              onPressed: () {
                // TODO: Navigate to add unit page
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Add Unit - Coming soon!')),
                );
              },
              icon: const Icon(Icons.add),
              label: const Text('Add Unit'),
            )
          : null,
    );
  }

  IconData _getTypeIcon(PropertyType type) {
    switch (type) {
      case PropertyType.singleFamily:
        return Icons.home;
      case PropertyType.multiFamily:
        return Icons.holiday_village;
      case PropertyType.apartment:
        return Icons.apartment;
      case PropertyType.condo:
        return Icons.domain;
      case PropertyType.townhouse:
        return Icons.home_work;
      case PropertyType.commercial:
        return Icons.business;
      case PropertyType.industrial:
        return Icons.factory;
      case PropertyType.mixed:
        return Icons.location_city;
    }
  }

  IconData _getStatusIcon(PropertyStatus status) {
    switch (status) {
      case PropertyStatus.active:
        return Icons.check_circle;
      case PropertyStatus.inactive:
        return Icons.pause_circle;
      case PropertyStatus.maintenance:
        return Icons.build_circle;
      case PropertyStatus.listed:
        return Icons.sell;
      case PropertyStatus.pending:
        return Icons.pending;
    }
  }

  Color _getStatusColor(PropertyStatus status) {
    switch (status) {
      case PropertyStatus.active:
        return Colors.green;
      case PropertyStatus.inactive:
        return Colors.grey;
      case PropertyStatus.maintenance:
        return Colors.orange;
      case PropertyStatus.listed:
        return Colors.blue;
      case PropertyStatus.pending:
        return Colors.purple;
    }
  }

  Color _getOccupancyColor(double rate) {
    if (rate >= 90) return Colors.green;
    if (rate >= 70) return Colors.orange;
    return Colors.red;
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year}';
  }
}

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

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 20, color: theme.colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const Divider(),
            ...children,
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const _InfoRow({
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.outline,
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
