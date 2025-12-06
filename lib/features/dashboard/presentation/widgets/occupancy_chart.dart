import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:somni_property/features/dashboard/domain/entities/dashboard_stats.dart';

/// Occupancy chart widget showing occupancy as a donut chart
class OccupancyChart extends StatelessWidget {
  final OccupancyStats stats;
  final double? size;

  const OccupancyChart({
    super.key,
    required this.stats,
    this.size,
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
              'Occupancy Rate',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 24),
            Center(
              child: SizedBox(
                height: size ?? 200,
                width: size ?? 200,
                child: Stack(
                  children: [
                    PieChart(
                      _buildPieChartData(context),
                    ),
                    Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            '${stats.occupancyRate.toStringAsFixed(1)}%',
                            style: Theme.of(context)
                                .textTheme
                                .headlineMedium
                                ?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                          ),
                          Text(
                            'Occupied',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: Theme.of(context)
                                      .colorScheme
                                      .onSurface
                                      .withOpacity(0.6),
                                ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildLegend(context),
          ],
        ),
      ),
    );
  }

  PieChartData _buildPieChartData(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return PieChartData(
      sectionsSpace: 2,
      centerSpaceRadius: 60,
      sections: [
        PieChartSectionData(
          color: colorScheme.primary,
          value: stats.occupiedUnits.toDouble(),
          title: stats.occupiedUnits.toString(),
          radius: 40,
          titleStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        PieChartSectionData(
          color: colorScheme.surfaceContainerHighest,
          value: stats.availableUnits.toDouble(),
          title: stats.availableUnits.toString(),
          radius: 40,
          titleStyle: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: colorScheme.onSurface.withOpacity(0.8),
          ),
        ),
      ],
    );
  }

  Widget _buildLegend(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        _buildLegendItem(
          context,
          color: colorScheme.primary,
          label: 'Occupied',
          value: '${stats.occupiedUnits} units',
        ),
        _buildLegendItem(
          context,
          color: colorScheme.surfaceContainerHighest,
          label: 'Available',
          value: '${stats.availableUnits} units',
        ),
      ],
    );
  }

  Widget _buildLegendItem(
    BuildContext context, {
    required Color color,
    required String label,
    required String value,
  }) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withOpacity(0.6),
                  ),
            ),
            Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Work order status chart (bar chart)
class WorkOrderChart extends StatelessWidget {
  final WorkOrderStats stats;
  final double? height;

  const WorkOrderChart({
    super.key,
    required this.stats,
    this.height,
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
              'Work Orders Status',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: height ?? 200,
              child: BarChart(
                _buildBarChartData(context),
              ),
            ),
          ],
        ),
      ),
    );
  }

  BarChartData _buildBarChartData(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return BarChartData(
      alignment: BarChartAlignment.spaceAround,
      maxY: [
        stats.openCount,
        stats.inProgressCount,
        stats.completedCount,
      ].reduce((a, b) => a > b ? a : b).toDouble() * 1.2,
      barTouchData: BarTouchData(
        enabled: true,
        touchTooltipData: BarTouchTooltipData(
          getTooltipColor: (group) => colorScheme.surfaceContainerHighest,
          getTooltipItem: (group, groupIndex, rod, rodIndex) {
            String label;
            switch (group.x) {
              case 0:
                label = 'Open';
                break;
              case 1:
                label = 'In Progress';
                break;
              case 2:
                label = 'Completed';
                break;
              default:
                label = '';
            }
            return BarTooltipItem(
              '$label\n${rod.toY.toInt()}',
              TextStyle(
                color: colorScheme.onSurface,
                fontWeight: FontWeight.bold,
              ),
            );
          },
        ),
      ),
      titlesData: FlTitlesData(
        show: true,
        rightTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        topTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            getTitlesWidget: (value, meta) {
              const style = TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
              );
              String text;
              switch (value.toInt()) {
                case 0:
                  text = 'Open';
                  break;
                case 1:
                  text = 'Progress';
                  break;
                case 2:
                  text = 'Done';
                  break;
                default:
                  text = '';
              }
              return Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(text, style: style),
              );
            },
          ),
        ),
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 30,
            getTitlesWidget: (value, meta) {
              return Text(
                value.toInt().toString(),
                style: TextStyle(
                  fontSize: 10,
                  color: colorScheme.onSurface.withOpacity(0.6),
                ),
              );
            },
          ),
        ),
      ),
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: 5,
        getDrawingHorizontalLine: (value) {
          return FlLine(
            color: colorScheme.outline.withOpacity(0.2),
            strokeWidth: 1,
          );
        },
      ),
      borderData: FlBorderData(
        show: true,
        border: Border(
          bottom: BorderSide(
            color: colorScheme.outline.withOpacity(0.2),
          ),
          left: BorderSide(
            color: colorScheme.outline.withOpacity(0.2),
          ),
        ),
      ),
      barGroups: [
        BarChartGroupData(
          x: 0,
          barRods: [
            BarChartRodData(
              toY: stats.openCount.toDouble(),
              color: Colors.orange,
              width: 20,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
            ),
          ],
        ),
        BarChartGroupData(
          x: 1,
          barRods: [
            BarChartRodData(
              toY: stats.inProgressCount.toDouble(),
              color: Colors.blue,
              width: 20,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
            ),
          ],
        ),
        BarChartGroupData(
          x: 2,
          barRods: [
            BarChartRodData(
              toY: stats.completedCount.toDouble(),
              color: Colors.green,
              width: 20,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
            ),
          ],
        ),
      ],
    );
  }
}
