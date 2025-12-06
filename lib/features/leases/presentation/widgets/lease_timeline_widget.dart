import 'package:flutter/material.dart';
import 'package:somni_property/features/leases/domain/entities/lease.dart';

/// Timeline widget showing lease lifecycle visually
class LeaseTimelineWidget extends StatelessWidget {
  final Lease lease;

  const LeaseTimelineWidget({super.key, required this.lease});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    // Calculate progress
    final now = DateTime.now();
    final totalDays = lease.endDate.difference(lease.startDate).inDays;
    final elapsedDays = now.difference(lease.startDate).inDays;
    final progress = (elapsedDays / totalDays).clamp(0.0, 1.0);

    // Determine timeline events
    final events = <TimelineEvent>[
      TimelineEvent(
        title: 'Lease Start',
        date: lease.startDate,
        icon: Icons.play_arrow,
        color: Colors.blue,
        isCompleted: true,
      ),
      if (lease.moveInDate != null)
        TimelineEvent(
          title: 'Move In',
          date: lease.moveInDate!,
          icon: Icons.home,
          color: Colors.green,
          isCompleted: true,
        ),
      if (lease.isPendingRenewal)
        TimelineEvent(
          title: 'Renewal Pending',
          date: DateTime.now(),
          icon: Icons.pending,
          color: Colors.orange,
          isCompleted: false,
        ),
      if (lease.isExpiringSoon && !lease.isPendingRenewal)
        TimelineEvent(
          title: 'Expiring Soon',
          date: lease.endDate.subtract(const Duration(days: 30)),
          icon: Icons.warning,
          color: Colors.orange,
          isCompleted: elapsedDays >= totalDays - 30,
        ),
      if (lease.moveOutDate != null)
        TimelineEvent(
          title: 'Move Out',
          date: lease.moveOutDate!,
          icon: Icons.exit_to_app,
          color: Colors.red,
          isCompleted: true,
        ),
      TimelineEvent(
        title: lease.status == LeaseStatus.terminated
            ? 'Terminated'
            : 'Lease End',
        date: lease.endDate,
        icon: lease.status == LeaseStatus.terminated
            ? Icons.cancel
            : Icons.event_busy,
        color: lease.status == LeaseStatus.terminated
            ? Colors.red
            : Colors.grey,
        isCompleted: lease.hasExpired || lease.status == LeaseStatus.terminated,
      ),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.timeline, color: colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  'Lease Timeline',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Progress bar
            if (lease.isActive) ...[
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        '${(progress * 100).toStringAsFixed(0)}% Complete',
                        style: theme.textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        '${lease.daysUntilExpiry} days remaining',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: LinearProgressIndicator(
                      value: progress,
                      minHeight: 8,
                      backgroundColor: colorScheme.surfaceContainerHighest,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        lease.isExpiringSoon ? Colors.orange : Colors.green,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
            ],

            // Timeline events
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: events.length,
              itemBuilder: (context, index) {
                final event = events[index];
                final isLast = index == events.length - 1;

                return _TimelineEventTile(
                  event: event,
                  isLast: isLast,
                  theme: theme,
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

/// Timeline event data model
class TimelineEvent {
  final String title;
  final DateTime date;
  final IconData icon;
  final Color color;
  final bool isCompleted;

  TimelineEvent({
    required this.title,
    required this.date,
    required this.icon,
    required this.color,
    required this.isCompleted,
  });
}

/// Timeline event tile widget
class _TimelineEventTile extends StatelessWidget {
  final TimelineEvent event;
  final bool isLast;
  final ThemeData theme;

  const _TimelineEventTile({
    required this.event,
    required this.isLast,
    required this.theme,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = theme.colorScheme;

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline indicator
          Column(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: event.isCompleted
                      ? event.color.withOpacity(0.1)
                      : colorScheme.surfaceContainerHighest,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: event.isCompleted ? event.color : colorScheme.outline,
                    width: 2,
                  ),
                ),
                child: Icon(
                  event.icon,
                  size: 20,
                  color: event.isCompleted ? event.color : colorScheme.outline,
                ),
              ),
              if (!isLast)
                Expanded(
                  child: Container(
                    width: 2,
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    color: event.isCompleted
                        ? event.color.withOpacity(0.3)
                        : colorScheme.outlineVariant,
                  ),
                ),
            ],
          ),
          const SizedBox(width: 16),

          // Event details
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    event.title,
                    style: theme.textTheme.bodyLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: event.isCompleted
                          ? colorScheme.onSurface
                          : colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _formatDate(event.date),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  if (event.isCompleted)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Row(
                        children: [
                          Icon(
                            Icons.check_circle,
                            size: 14,
                            color: event.color,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'Completed',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: event.color,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year}';
  }
}
