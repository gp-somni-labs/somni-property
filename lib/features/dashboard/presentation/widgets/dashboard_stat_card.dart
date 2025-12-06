import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:somni_property/features/dashboard/domain/entities/dashboard_stats.dart';

/// Stat card widget for displaying key metrics
class DashboardStatCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;
  final TrendIndicator? trend;
  final double? trendValue;
  final VoidCallback? onTap;
  final String? subtitle;

  const DashboardStatCard({
    super.key,
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
    this.trend,
    this.trendValue,
    this.onTap,
    this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Icon and trend indicator
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(icon, color: color, size: 24),
                  ),
                  if (trend != null && trendValue != null)
                    _buildTrendIndicator(),
                ],
              ),
              const Spacer(),

              // Value
              Text(
                value,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),

              // Title and subtitle
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSurface
                              .withOpacity(0.7),
                        ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (subtitle != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      subtitle!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurface
                                .withOpacity(0.5),
                          ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTrendIndicator() {
    IconData trendIcon;
    Color trendColor;

    switch (trend!) {
      case TrendIndicator.up:
        trendIcon = Icons.trending_up;
        trendColor = Colors.green;
        break;
      case TrendIndicator.down:
        trendIcon = Icons.trending_down;
        trendColor = Colors.red;
        break;
      case TrendIndicator.neutral:
        trendIcon = Icons.trending_flat;
        trendColor = Colors.grey;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: trendColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(trendIcon, color: trendColor, size: 14),
          const SizedBox(width: 2),
          Text(
            '${trendValue!.abs().toStringAsFixed(1)}%',
            style: TextStyle(
              color: trendColor,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

/// Grid of stat cards
class DashboardStatsGrid extends StatelessWidget {
  final Map<String, dynamic> stats;
  final Function(String)? onCardTap;

  const DashboardStatsGrid({
    super.key,
    required this.stats,
    this.onCardTap,
  });

  @override
  Widget build(BuildContext context) {
    final currencyFormat = NumberFormat.currency(symbol: '\$', decimalDigits: 0);
    final percentFormat = NumberFormat.percentPattern()..maximumFractionDigits = 1;

    final cards = [
      DashboardStatCard(
        title: 'Total Properties',
        value: stats['totalProperties']?.toString() ?? '0',
        icon: Icons.apartment,
        color: Colors.blue,
        trend: stats['propertyTrend'] as TrendIndicator?,
        trendValue: stats['propertyTrendValue'] as double?,
        onTap: () => onCardTap?.call('properties'),
      ),
      DashboardStatCard(
        title: 'Active Tenants',
        value: stats['activeTenants']?.toString() ?? '0',
        icon: Icons.people,
        color: Colors.green,
        trend: stats['tenantTrend'] as TrendIndicator?,
        trendValue: stats['tenantTrendValue'] as double?,
        subtitle: '${stats['occupancyRate']?.toStringAsFixed(1) ?? '0'}% occupied',
        onTap: () => onCardTap?.call('tenants'),
      ),
      DashboardStatCard(
        title: 'Monthly Revenue',
        value: currencyFormat.format(stats['monthlyRevenue'] ?? 0),
        icon: Icons.attach_money,
        color: Colors.amber,
        trend: stats['revenueTrend'] as TrendIndicator?,
        trendValue: stats['revenueTrendValue'] as double?,
        onTap: () => onCardTap?.call('payments'),
      ),
      DashboardStatCard(
        title: 'Open Work Orders',
        value: stats['openWorkOrders']?.toString() ?? '0',
        icon: Icons.build,
        color: stats['openWorkOrders'] != null && stats['openWorkOrders'] > 0
            ? Colors.orange
            : Colors.grey,
        subtitle: stats['criticalWorkOrders'] != null &&
                stats['criticalWorkOrders'] > 0
            ? '${stats['criticalWorkOrders']} critical'
            : null,
        onTap: () => onCardTap?.call('work-orders'),
      ),
      DashboardStatCard(
        title: 'Available Units',
        value: stats['availableUnits']?.toString() ?? '0',
        icon: Icons.meeting_room,
        color: Colors.teal,
        subtitle: stats['totalUnits'] != null
            ? 'of ${stats['totalUnits']} total'
            : null,
        onTap: () => onCardTap?.call('properties'),
      ),
      DashboardStatCard(
        title: 'Overdue Payments',
        value: currencyFormat.format(stats['overduePayments'] ?? 0),
        icon: Icons.warning,
        color: stats['overduePayments'] != null && stats['overduePayments'] > 0
            ? Colors.red
            : Colors.grey,
        onTap: () => onCardTap?.call('payments'),
      ),
    ];

    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: _getCrossAxisCount(context),
      mainAxisSpacing: 16,
      crossAxisSpacing: 16,
      childAspectRatio: _getAspectRatio(context),
      children: cards,
    );
  }

  int _getCrossAxisCount(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    if (width > 1200) return 4;
    if (width > 800) return 3;
    if (width > 600) return 2;
    return 2;
  }

  double _getAspectRatio(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    if (width > 1200) return 1.4;
    if (width > 800) return 1.3;
    if (width > 600) return 1.2;
    return 1.1;
  }
}
