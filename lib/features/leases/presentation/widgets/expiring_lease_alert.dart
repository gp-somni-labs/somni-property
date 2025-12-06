import 'package:flutter/material.dart';
import 'package:somni_property/features/leases/domain/entities/lease.dart';

/// Alert banner for expiring leases
class ExpiringLeaseAlert extends StatelessWidget {
  final Lease lease;
  final VoidCallback? onRenew;
  final VoidCallback? onViewDetails;

  const ExpiringLeaseAlert({
    super.key,
    required this.lease,
    this.onRenew,
    this.onViewDetails,
  });

  @override
  Widget build(BuildContext context) {
    if (!lease.isExpiringSoon) return const SizedBox.shrink();

    final theme = Theme.of(context);
    final daysLeft = lease.daysUntilExpiry;

    // Determine urgency level
    Color backgroundColor;
    Color borderColor;
    Color iconColor;
    IconData icon;
    String urgencyText;

    if (daysLeft <= 7) {
      // Critical - 7 days or less
      backgroundColor = Colors.red.shade50;
      borderColor = Colors.red.shade300;
      iconColor = Colors.red.shade700;
      icon = Icons.error;
      urgencyText = 'URGENT';
    } else if (daysLeft <= 14) {
      // High urgency - 2 weeks or less
      backgroundColor = Colors.deepOrange.shade50;
      borderColor = Colors.deepOrange.shade300;
      iconColor = Colors.deepOrange.shade700;
      icon = Icons.warning;
      urgencyText = 'HIGH PRIORITY';
    } else {
      // Normal alert - within 30 days
      backgroundColor = Colors.orange.shade50;
      borderColor = Colors.orange.shade300;
      iconColor = Colors.orange.shade700;
      icon = Icons.warning_amber;
      urgencyText = 'ATTENTION';
    }

    return Container(
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor, width: 2),
        boxShadow: [
          BoxShadow(
            color: borderColor.withOpacity(0.2),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: borderColor.withOpacity(0.1),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(10),
                topRight: Radius.circular(10),
              ),
            ),
            child: Row(
              children: [
                Icon(icon, color: iconColor, size: 24),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        urgencyText,
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: iconColor,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1.2,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Lease Expiring Soon',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: iconColor,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: iconColor,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '$daysLeft days',
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Content
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Lease details
                Row(
                  children: [
                    Icon(Icons.person, size: 18, color: iconColor),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        lease.tenantName ?? 'Tenant #${lease.tenantId}',
                        style: theme.textTheme.bodyLarge?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(Icons.home, size: 18, color: iconColor),
                    const SizedBox(width: 8),
                    Text(
                      lease.unitNumber != null
                          ? 'Unit ${lease.unitNumber}'
                          : 'Unit #${lease.unitId}',
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(Icons.event, size: 18, color: iconColor),
                    const SizedBox(width: 8),
                    Text(
                      'Expires: ${_formatDate(lease.endDate)}',
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(Icons.attach_money, size: 18, color: iconColor),
                    const SizedBox(width: 8),
                    Text(
                      '\$${lease.monthlyRent.toStringAsFixed(0)}/month',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),

                // Action message
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.info_outline, color: iconColor, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Contact the tenant to discuss lease renewal or move-out plans.',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurface,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                // Actions
                const SizedBox(height: 16),
                Row(
                  children: [
                    if (onRenew != null)
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: onRenew,
                          icon: const Icon(Icons.autorenew, size: 18),
                          label: const Text('Renew Lease'),
                          style: FilledButton.styleFrom(
                            backgroundColor: iconColor,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ),
                    if (onRenew != null && onViewDetails != null)
                      const SizedBox(width: 12),
                    if (onViewDetails != null)
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: onViewDetails,
                          icon: Icon(Icons.visibility, size: 18, color: iconColor),
                          label: Text(
                            'View Details',
                            style: TextStyle(color: iconColor),
                          ),
                          style: OutlinedButton.styleFrom(
                            side: BorderSide(color: iconColor, width: 2),
                          ),
                        ),
                      ),
                  ],
                ),
              ],
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

/// Compact version for list displays
class ExpiringLeaseCompactAlert extends StatelessWidget {
  final Lease lease;
  final VoidCallback? onTap;

  const ExpiringLeaseCompactAlert({
    super.key,
    required this.lease,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    if (!lease.isExpiringSoon) return const SizedBox.shrink();

    final theme = Theme.of(context);
    final daysLeft = lease.daysUntilExpiry;

    Color backgroundColor;
    Color textColor;
    IconData icon;

    if (daysLeft <= 7) {
      backgroundColor = Colors.red.shade100;
      textColor = Colors.red.shade900;
      icon = Icons.error;
    } else if (daysLeft <= 14) {
      backgroundColor = Colors.deepOrange.shade100;
      textColor = Colors.deepOrange.shade900;
      icon = Icons.warning;
    } else {
      backgroundColor = Colors.orange.shade100;
      textColor = Colors.orange.shade900;
      icon = Icons.warning_amber;
    }

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: backgroundColor,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: textColor.withOpacity(0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: textColor, size: 18),
            const SizedBox(width: 8),
            Text(
              'Expires in $daysLeft days',
              style: theme.textTheme.bodySmall?.copyWith(
                color: textColor,
                fontWeight: FontWeight.w600,
              ),
            ),
            if (onTap != null) ...[
              const SizedBox(width: 4),
              Icon(Icons.arrow_forward, color: textColor, size: 16),
            ],
          ],
        ),
      ),
    );
  }
}
