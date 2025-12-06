import 'package:flutter/material.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';

/// Card widget displaying payment summary information
class PaymentCard extends StatelessWidget {
  final Payment payment;
  final VoidCallback? onTap;
  final VoidCallback? onRecord;
  final VoidCallback? onApplyLateFee;

  const PaymentCard({
    super.key,
    required this.payment,
    this.onTap,
    this.onRecord,
    this.onApplyLateFee,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: _getStatusColor(payment.status).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(
                      _getTypeIcon(payment.type),
                      color: _getStatusColor(payment.status),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          payment.type.displayName,
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (payment.tenantName != null)
                          Text(
                            payment.tenantName!,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                            ),
                          ),
                      ],
                    ),
                  ),
                  _StatusChip(status: payment.status),
                ],
              ),
              const SizedBox(height: 16),
              const Divider(height: 1),
              const SizedBox(height: 16),

              // Amount and Date
              Row(
                children: [
                  Expanded(
                    child: _DetailItem(
                      icon: Icons.attach_money,
                      label: 'Amount',
                      value: payment.formattedTotalAmount,
                      highlight: true,
                    ),
                  ),
                  Expanded(
                    child: _DetailItem(
                      icon: Icons.calendar_today,
                      label: 'Due Date',
                      value: payment.formattedDueDate,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  if (payment.unitNumber != null)
                    Expanded(
                      child: _DetailItem(
                        icon: Icons.apartment,
                        label: 'Unit',
                        value: payment.unitNumber!,
                      ),
                    ),
                  if (payment.paidDate != null)
                    Expanded(
                      child: _DetailItem(
                        icon: Icons.check_circle,
                        label: 'Paid',
                        value: payment.formattedPaidDate!,
                      ),
                    ),
                ],
              ),

              // Late fee indicator
              if (payment.hasLateFee) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.warning_amber,
                        color: Colors.red.shade700,
                        size: 18,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Late Fee: \$${payment.lateFee!.toStringAsFixed(2)}',
                        style: TextStyle(
                          color: Colors.red.shade800,
                          fontWeight: FontWeight.w500,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              // Overdue warning
              if (payment.isOverdue && payment.status == PaymentStatus.pending) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.orange.shade200),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.schedule,
                        color: Colors.orange.shade700,
                        size: 18,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Overdue by ${payment.daysOverdue} days',
                        style: TextStyle(
                          color: Colors.orange.shade800,
                          fontWeight: FontWeight.w500,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              // Actions
              if ((onRecord != null || onApplyLateFee != null) &&
                  payment.status == PaymentStatus.pending) ...[
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    if (onRecord != null)
                      FilledButton.icon(
                        onPressed: onRecord,
                        icon: const Icon(Icons.payment, size: 18),
                        label: const Text('Record Payment'),
                        style: FilledButton.styleFrom(
                          backgroundColor: Colors.green,
                        ),
                      ),
                    if (onRecord != null && onApplyLateFee != null && payment.isOverdue)
                      const SizedBox(width: 8),
                    if (onApplyLateFee != null && payment.isOverdue && !payment.hasLateFee)
                      OutlinedButton.icon(
                        onPressed: onApplyLateFee,
                        icon: Icon(Icons.add_circle_outline, size: 18, color: colorScheme.error),
                        label: Text('Late Fee', style: TextStyle(color: colorScheme.error)),
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Color _getStatusColor(PaymentStatus status) {
    switch (status) {
      case PaymentStatus.paid:
        return Colors.green;
      case PaymentStatus.pending:
        return Colors.orange;
      case PaymentStatus.partial:
        return Colors.blue;
      case PaymentStatus.overdue:
        return Colors.red;
      case PaymentStatus.cancelled:
        return Colors.grey;
      case PaymentStatus.refunded:
        return Colors.purple;
    }
  }

  IconData _getTypeIcon(PaymentType type) {
    switch (type) {
      case PaymentType.rent:
        return Icons.home;
      case PaymentType.deposit:
        return Icons.security;
      case PaymentType.lateFee:
        return Icons.warning;
      case PaymentType.utility:
        return Icons.bolt;
      case PaymentType.maintenance:
        return Icons.build;
      case PaymentType.other:
        return Icons.receipt;
    }
  }
}

/// Status indicator chip
class _StatusChip extends StatelessWidget {
  final PaymentStatus status;

  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    Color backgroundColor;
    Color textColor;

    switch (status) {
      case PaymentStatus.paid:
        backgroundColor = Colors.green.shade100;
        textColor = Colors.green.shade800;
        break;
      case PaymentStatus.pending:
        backgroundColor = Colors.orange.shade100;
        textColor = Colors.orange.shade800;
        break;
      case PaymentStatus.partial:
        backgroundColor = Colors.blue.shade100;
        textColor = Colors.blue.shade800;
        break;
      case PaymentStatus.overdue:
        backgroundColor = Colors.red.shade100;
        textColor = Colors.red.shade800;
        break;
      case PaymentStatus.cancelled:
        backgroundColor = Colors.grey.shade200;
        textColor = Colors.grey.shade700;
        break;
      case PaymentStatus.refunded:
        backgroundColor = Colors.purple.shade100;
        textColor = Colors.purple.shade800;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        status.displayName,
        style: TextStyle(
          color: textColor,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

/// Detail item widget
class _DetailItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final bool highlight;

  const _DetailItem({
    required this.icon,
    required this.label,
    required this.value,
    this.highlight = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Row(
      children: [
        Icon(icon, size: 16, color: colorScheme.outline),
        const SizedBox(width: 6),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
                fontSize: 11,
              ),
            ),
            Text(
              value,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
                color: highlight ? colorScheme.primary : null,
                fontSize: highlight ? 16 : null,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Stats card for payment dashboard
class PaymentStatsCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color? color;

  const PaymentStatsCard({
    super.key,
    required this.title,
    required this.value,
    required this.icon,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final cardColor = color ?? colorScheme.primary;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: cardColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: cardColor, size: 20),
            ),
            const SizedBox(height: 12),
            Text(
              value,
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: cardColor,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
