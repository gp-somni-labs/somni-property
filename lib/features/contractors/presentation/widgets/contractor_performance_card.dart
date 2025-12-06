import 'package:flutter/material.dart';
import 'package:somni_property/features/contractors/domain/entities/contractor.dart';

/// Card displaying contractor performance metrics
class ContractorPerformanceCard extends StatelessWidget {
  final ContractorPerformance performance;

  const ContractorPerformanceCard({
    super.key,
    required this.performance,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Performance Metrics',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),

            // Jobs metrics
            Row(
              children: [
                Expanded(
                  child: _MetricItem(
                    label: 'Total Jobs',
                    value: performance.totalJobs.toString(),
                    icon: Icons.work_outline,
                    color: Colors.blue,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _MetricItem(
                    label: 'Completed',
                    value: performance.completedJobs.toString(),
                    icon: Icons.check_circle_outline,
                    color: Colors.green,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Time and rating metrics
            Row(
              children: [
                Expanded(
                  child: _MetricItem(
                    label: 'Avg Time',
                    value: '${performance.averageCompletionTime.toStringAsFixed(1)}h',
                    icon: Icons.schedule,
                    color: Colors.orange,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _MetricItem(
                    label: 'On-Time %',
                    value: '${performance.onTimePercentage.toStringAsFixed(0)}%',
                    icon: Icons.access_time,
                    color: Colors.purple,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Revenue metric
            _MetricItem(
              label: 'Total Revenue',
              value: '\$${performance.totalRevenue.toStringAsFixed(2)}',
              icon: Icons.attach_money,
              color: Colors.teal,
              isLarge: true,
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricItem extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;
  final bool isLarge;

  const _MetricItem({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
    this.isLarge = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment:
            isLarge ? CrossAxisAlignment.start : CrossAxisAlignment.center,
        children: [
          Row(
            mainAxisAlignment:
                isLarge ? MainAxisAlignment.start : MainAxisAlignment.center,
            children: [
              Icon(icon, color: color, size: isLarge ? 24 : 20),
              if (isLarge) const SizedBox(width: 8),
              if (isLarge)
                Text(
                  label,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: color,
                  fontSize: isLarge ? 28 : null,
                ),
          ),
          if (!isLarge) ...[
            const SizedBox(height: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    );
  }
}
