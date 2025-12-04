import 'package:flutter/material.dart';
import 'package:somni_property/features/properties/domain/entities/property.dart';

/// Card widget for displaying a property in a grid/list
class PropertyCard extends StatelessWidget {
  final Property property;
  final VoidCallback? onTap;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  const PropertyCard({
    super.key,
    required this.property,
    this.onTap,
    this.onEdit,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with image or placeholder
            Container(
              height: 100,
              width: double.infinity,
              decoration: BoxDecoration(
                color: _getTypeColor(property.type).withOpacity(0.2),
              ),
              child: Stack(
                children: [
                  // Type icon
                  Center(
                    child: Icon(
                      _getTypeIcon(property.type),
                      size: 48,
                      color: _getTypeColor(property.type),
                    ),
                  ),
                  // Status badge
                  Positioned(
                    top: 8,
                    right: 8,
                    child: _StatusBadge(status: property.status),
                  ),
                  // Menu button
                  if (onEdit != null || onDelete != null)
                    Positioned(
                      top: 4,
                      left: 4,
                      child: PopupMenuButton<String>(
                        icon: Icon(
                          Icons.more_vert,
                          color: colorScheme.onSurfaceVariant,
                        ),
                        itemBuilder: (context) => [
                          if (onEdit != null)
                            const PopupMenuItem(
                              value: 'edit',
                              child: Row(
                                children: [
                                  Icon(Icons.edit, size: 20),
                                  SizedBox(width: 12),
                                  Text('Edit'),
                                ],
                              ),
                            ),
                          if (onDelete != null)
                            PopupMenuItem(
                              value: 'delete',
                              child: Row(
                                children: [
                                  Icon(Icons.delete, size: 20, color: colorScheme.error),
                                  const SizedBox(width: 12),
                                  Text('Delete', style: TextStyle(color: colorScheme.error)),
                                ],
                              ),
                            ),
                        ],
                        onSelected: (value) {
                          if (value == 'edit') onEdit?.call();
                          if (value == 'delete') onDelete?.call();
                        },
                      ),
                    ),
                ],
              ),
            ),

            // Content
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Property name
                    Text(
                      property.name,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),

                    // Address
                    Row(
                      children: [
                        Icon(
                          Icons.location_on_outlined,
                          size: 14,
                          color: colorScheme.outline,
                        ),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            '${property.city}, ${property.state}',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: colorScheme.outline,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),

                    // Type chip
                    Chip(
                      label: Text(
                        property.type.displayName,
                        style: theme.textTheme.labelSmall,
                      ),
                      padding: EdgeInsets.zero,
                      visualDensity: VisualDensity.compact,
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),

                    const Spacer(),

                    // Stats row
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        // Units
                        _StatItem(
                          icon: Icons.door_front_door_outlined,
                          label: '${property.occupiedUnits}/${property.totalUnits}',
                          tooltip: 'Occupied/Total Units',
                        ),
                        // Occupancy
                        _StatItem(
                          icon: Icons.pie_chart_outline,
                          label: '${property.occupancyRate.toStringAsFixed(0)}%',
                          tooltip: 'Occupancy Rate',
                          color: _getOccupancyColor(property.occupancyRate),
                        ),
                        // Revenue
                        if (property.monthlyRevenue != null)
                          _StatItem(
                            icon: Icons.attach_money,
                            label: _formatCurrency(property.monthlyRevenue!),
                            tooltip: 'Monthly Revenue',
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
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

  Color _getTypeColor(PropertyType type) {
    switch (type) {
      case PropertyType.singleFamily:
        return Colors.blue;
      case PropertyType.multiFamily:
        return Colors.purple;
      case PropertyType.apartment:
        return Colors.orange;
      case PropertyType.condo:
        return Colors.teal;
      case PropertyType.townhouse:
        return Colors.indigo;
      case PropertyType.commercial:
        return Colors.amber;
      case PropertyType.industrial:
        return Colors.grey;
      case PropertyType.mixed:
        return Colors.green;
    }
  }

  Color _getOccupancyColor(double rate) {
    if (rate >= 90) return Colors.green;
    if (rate >= 70) return Colors.orange;
    return Colors.red;
  }

  String _formatCurrency(double amount) {
    if (amount >= 1000) {
      return '\$${(amount / 1000).toStringAsFixed(1)}k';
    }
    return '\$${amount.toStringAsFixed(0)}';
  }
}

class _StatusBadge extends StatelessWidget {
  final PropertyStatus status;

  const _StatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _getStatusColor(status),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        status.displayName,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 10,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
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
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? tooltip;
  final Color? color;

  const _StatItem({
    required this.icon,
    required this.label,
    this.tooltip,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final effectiveColor = color ?? theme.colorScheme.onSurfaceVariant;

    final content = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: effectiveColor),
        const SizedBox(width: 4),
        Text(
          label,
          style: theme.textTheme.labelSmall?.copyWith(
            color: effectiveColor,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );

    if (tooltip != null) {
      return Tooltip(message: tooltip!, child: content);
    }
    return content;
  }
}
