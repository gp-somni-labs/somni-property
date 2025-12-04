import 'package:flutter/material.dart';
import 'package:somni_property/features/properties/presentation/providers/property_provider.dart';

/// Card showing property portfolio statistics
class PropertyStatsCard extends StatelessWidget {
  final PropertyStats stats;

  const PropertyStatsCard({super.key, required this.stats});

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
                Icon(
                  Icons.analytics_outlined,
                  color: colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'Portfolio Overview',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            LayoutBuilder(
              builder: (context, constraints) {
                // Use wrap for narrow screens
                if (constraints.maxWidth < 500) {
                  return Wrap(
                    spacing: 16,
                    runSpacing: 16,
                    children: _buildStatItems(context),
                  );
                }
                // Use row for wider screens
                return Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: _buildStatItems(context),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildStatItems(BuildContext context) {
    return [
      _StatItem(
        icon: Icons.home_work,
        value: stats.totalProperties.toString(),
        label: 'Properties',
        color: Colors.blue,
      ),
      _StatItem(
        icon: Icons.door_front_door,
        value: '${stats.occupiedUnits}/${stats.totalUnits}',
        label: 'Units Occupied',
        color: Colors.green,
      ),
      _StatItem(
        icon: Icons.pie_chart,
        value: '${stats.averageOccupancyRate.toStringAsFixed(1)}%',
        label: 'Occupancy',
        color: _getOccupancyColor(stats.averageOccupancyRate),
      ),
      _StatItem(
        icon: Icons.attach_money,
        value: _formatCurrency(stats.totalMonthlyRevenue),
        label: 'Monthly Revenue',
        color: Colors.amber.shade700,
      ),
    ];
  }

  Color _getOccupancyColor(double rate) {
    if (rate >= 90) return Colors.green;
    if (rate >= 70) return Colors.orange;
    return Colors.red;
  }

  String _formatCurrency(double amount) {
    if (amount >= 1000000) {
      return '\$${(amount / 1000000).toStringAsFixed(2)}M';
    }
    if (amount >= 1000) {
      return '\$${(amount / 1000).toStringAsFixed(1)}K';
    }
    return '\$${amount.toStringAsFixed(0)}';
  }
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;
  final Color color;

  const _StatItem({
    required this.icon,
    required this.value,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SizedBox(
      width: 100,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.outline,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
