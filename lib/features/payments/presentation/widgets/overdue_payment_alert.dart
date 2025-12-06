import 'package:flutter/material.dart';

/// Widget displaying an alert banner for overdue payments
class OverduePaymentAlert extends StatelessWidget {
  final int overdueCount;
  final double overdueAmount;
  final VoidCallback? onViewOverdue;

  const OverduePaymentAlert({
    super.key,
    required this.overdueCount,
    required this.overdueAmount,
    this.onViewOverdue,
  });

  @override
  Widget build(BuildContext context) {
    if (overdueCount == 0) return const SizedBox.shrink();

    final theme = Theme.of(context);

    return Container(
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        border: Border.all(color: Colors.red.shade200),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onViewOverdue,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.red.shade100,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    Icons.warning_amber,
                    color: Colors.red.shade700,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '$overdueCount Overdue Payment${overdueCount > 1 ? 's' : ''}',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: Colors.red.shade900,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '\$${overdueAmount.toStringAsFixed(2)} outstanding',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: Colors.red.shade700,
                        ),
                      ),
                    ],
                  ),
                ),
                if (onViewOverdue != null)
                  Icon(
                    Icons.arrow_forward_ios,
                    size: 16,
                    color: Colors.red.shade700,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
