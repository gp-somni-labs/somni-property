import 'package:flutter/material.dart';
import 'package:somni_property/features/dashboard/domain/entities/activity_item.dart';

/// Activity feed widget showing recent activities grouped by date
class ActivityFeed extends StatelessWidget {
  final List<ActivityItem> activities;
  final Function(ActivityItem)? onActivityTap;

  const ActivityFeed({
    super.key,
    required this.activities,
    this.onActivityTap,
  });

  @override
  Widget build(BuildContext context) {
    if (activities.isEmpty) {
      return _buildEmptyState(context);
    }

    // Group activities by date
    final grouped = _groupActivitiesByDate(activities);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Recent Activity',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton(
                  onPressed: () {
                    // TODO: Navigate to full activity log
                  },
                  child: const Text('View All'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...grouped.entries.map((entry) => _buildDateGroup(
                  context,
                  entry.key,
                  entry.value,
                )),
          ],
        ),
      ),
    );
  }

  Map<String, List<ActivityItem>> _groupActivitiesByDate(
      List<ActivityItem> items) {
    final groups = <String, List<ActivityItem>>{};
    final order = ['Today', 'Yesterday', 'This Week', 'Earlier'];

    for (final item in items) {
      final group = item.dateGroup;
      if (!groups.containsKey(group)) {
        groups[group] = [];
      }
      groups[group]!.add(item);
    }

    // Sort by predefined order
    final sortedGroups = <String, List<ActivityItem>>{};
    for (final key in order) {
      if (groups.containsKey(key)) {
        sortedGroups[key] = groups[key]!;
      }
    }

    return sortedGroups;
  }

  Widget _buildDateGroup(
      BuildContext context, String date, List<ActivityItem> items) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text(
            date,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context).colorScheme.primary,
                ),
          ),
        ),
        ...items.map((activity) => _buildActivityItem(context, activity)),
        const SizedBox(height: 8),
      ],
    );
  }

  Widget _buildActivityItem(BuildContext context, ActivityItem activity) {
    return InkWell(
      onTap: () => onActivityTap?.call(activity),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildActivityIcon(context, activity.type),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    activity.title,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    activity.description,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSurface
                              .withOpacity(0.7),
                        ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    activity.timeAgo,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSurface
                              .withOpacity(0.5),
                          fontSize: 11,
                        ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActivityIcon(BuildContext context, ActivityType type) {
    IconData icon;
    Color color;

    switch (type) {
      case ActivityType.propertyCreated:
      case ActivityType.propertyUpdated:
        icon = Icons.apartment;
        color = Colors.blue;
        break;
      case ActivityType.tenantAdded:
      case ActivityType.tenantRemoved:
        icon = Icons.people;
        color = Colors.green;
        break;
      case ActivityType.leaseCreated:
      case ActivityType.leaseExpiring:
      case ActivityType.leaseRenewed:
        icon = Icons.description;
        color = Colors.orange;
        break;
      case ActivityType.paymentReceived:
        icon = Icons.check_circle;
        color = Colors.green;
        break;
      case ActivityType.paymentOverdue:
        icon = Icons.warning;
        color = Colors.red;
        break;
      case ActivityType.workOrderCreated:
      case ActivityType.workOrderCompleted:
        icon = Icons.build;
        color = Colors.purple;
        break;
      case ActivityType.maintenanceScheduled:
        icon = Icons.schedule;
        color = Colors.teal;
        break;
      case ActivityType.documentUploaded:
        icon = Icons.upload_file;
        color = Colors.indigo;
        break;
      case ActivityType.systemAlert:
        icon = Icons.notifications;
        color = Colors.amber;
        break;
      default:
        icon = Icons.info;
        color = Colors.grey;
    }

    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        shape: BoxShape.circle,
      ),
      child: Icon(icon, color: color, size: 18),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.history,
                size: 48,
                color: Theme.of(context).colorScheme.outline,
              ),
              const SizedBox(height: 16),
              Text(
                'No recent activity',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color:
                          Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
