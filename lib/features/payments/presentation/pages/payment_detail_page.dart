import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';
import 'package:somni_property/features/payments/presentation/providers/payment_provider.dart';

/// Page displaying detailed payment information
class PaymentDetailPage extends ConsumerWidget {
  final String paymentId;

  const PaymentDetailPage({super.key, required this.paymentId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(paymentDetailProvider(paymentId));
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    if (state.isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Payment Details')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (state.error != null || state.payment == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Payment Details')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 64, color: colorScheme.error),
              const SizedBox(height: 16),
              Text(state.error ?? 'Payment not found'),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: () => context.pop(),
                icon: const Icon(Icons.arrow_back),
                label: const Text('Go Back'),
              ),
            ],
          ),
        ),
      );
    }

    final payment = state.payment!;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Payment Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () => context.push('/payments/${payment.id}/edit'),
          ),
          PopupMenuButton<String>(
            onSelected: (value) async {
              if (value == 'record' && payment.status == PaymentStatus.pending) {
                _showRecordPaymentDialog(context, ref, payment);
              } else if (value == 'late_fee') {
                _showApplyLateFeeDialog(context, ref, payment);
              } else if (value == 'cancel') {
                _showCancelDialog(context, ref, payment);
              } else if (value == 'refund') {
                _showRefundDialog(context, ref, payment);
              } else if (value == 'delete') {
                final confirmed = await _showDeleteDialog(context, payment);
                if (confirmed == true && context.mounted) {
                  final success = await ref
                      .read(paymentsProvider.notifier)
                      .deletePayment(payment.id);
                  if (context.mounted) {
                    if (success) {
                      context.pop();
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Failed to delete payment'),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  }
                }
              }
            },
            itemBuilder: (context) => [
              if (payment.status == PaymentStatus.pending)
                const PopupMenuItem(
                  value: 'record',
                  child: Row(
                    children: [
                      Icon(Icons.check_circle, color: Colors.green),
                      SizedBox(width: 8),
                      Text('Record Payment'),
                    ],
                  ),
                ),
              if (payment.status == PaymentStatus.pending && payment.isOverdue && !payment.hasLateFee)
                const PopupMenuItem(
                  value: 'late_fee',
                  child: Row(
                    children: [
                      Icon(Icons.add_circle, color: Colors.orange),
                      SizedBox(width: 8),
                      Text('Apply Late Fee'),
                    ],
                  ),
                ),
              if (payment.status == PaymentStatus.pending)
                PopupMenuItem(
                  value: 'cancel',
                  child: Row(
                    children: [
                      Icon(Icons.cancel, color: colorScheme.error),
                      const SizedBox(width: 8),
                      Text('Cancel', style: TextStyle(color: colorScheme.error)),
                    ],
                  ),
                ),
              if (payment.status == PaymentStatus.paid)
                PopupMenuItem(
                  value: 'refund',
                  child: Row(
                    children: [
                      Icon(Icons.undo, color: colorScheme.error),
                      const SizedBox(width: 8),
                      Text('Refund', style: TextStyle(color: colorScheme.error)),
                    ],
                  ),
                ),
              PopupMenuItem(
                value: 'delete',
                child: Row(
                  children: [
                    Icon(Icons.delete_outline, color: colorScheme.error),
                    const SizedBox(width: 8),
                    Text('Delete', style: TextStyle(color: colorScheme.error)),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () =>
            ref.read(paymentDetailProvider(paymentId).notifier).refresh(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Status Header
              _StatusHeader(payment: payment),
              const SizedBox(height: 24),

              // Amount Details
              _SectionCard(
                title: 'Amount Details',
                icon: Icons.attach_money,
                children: [
                  _InfoRow(
                    icon: Icons.payments,
                    label: 'Amount',
                    value: payment.formattedAmount,
                  ),
                  if (payment.hasLateFee)
                    _InfoRow(
                      icon: Icons.warning,
                      label: 'Late Fee',
                      value: '\$${payment.lateFee!.toStringAsFixed(2)}',
                      valueColor: Colors.red,
                    ),
                  _InfoRow(
                    icon: Icons.calculate,
                    label: 'Total',
                    value: payment.formattedTotalAmount,
                    valueColor: colorScheme.primary,
                    highlight: true,
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Payment Info
              _SectionCard(
                title: 'Payment Information',
                icon: Icons.info_outline,
                children: [
                  _InfoRow(
                    icon: Icons.category,
                    label: 'Type',
                    value: payment.type.displayName,
                  ),
                  _InfoRow(
                    icon: Icons.calendar_today,
                    label: 'Due Date',
                    value: payment.formattedDueDate,
                  ),
                  if (payment.paidDate != null)
                    _InfoRow(
                      icon: Icons.check_circle,
                      label: 'Paid Date',
                      value: payment.formattedPaidDate!,
                    ),
                  if (payment.method != null)
                    _InfoRow(
                      icon: Icons.payment,
                      label: 'Method',
                      value: payment.method!.displayName,
                    ),
                  if (payment.transactionId != null)
                    _InfoRow(
                      icon: Icons.receipt,
                      label: 'Transaction ID',
                      value: payment.transactionId!,
                    ),
                ],
              ),
              const SizedBox(height: 16),

              // Unit & Tenant
              _SectionCard(
                title: 'Associated Records',
                icon: Icons.link,
                children: [
                  _InfoRow(
                    icon: Icons.apartment,
                    label: 'Unit',
                    value: payment.unitNumber ?? 'Unit #${payment.unitId}',
                  ),
                  _InfoRow(
                    icon: Icons.person,
                    label: 'Tenant',
                    value: payment.tenantName ?? 'Tenant #${payment.tenantId}',
                  ),
                  _InfoRow(
                    icon: Icons.description,
                    label: 'Lease',
                    value: 'Lease #${payment.leaseId}',
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Notes
              if (payment.notes != null && payment.notes!.isNotEmpty)
                _SectionCard(
                  title: 'Notes',
                  icon: Icons.notes,
                  children: [
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Text(payment.notes!),
                    ),
                  ],
                ),
              if (payment.notes != null && payment.notes!.isNotEmpty)
                const SizedBox(height: 16),

              // Quick Actions
              if (payment.status == PaymentStatus.pending)
                _SectionCard(
                  title: 'Quick Actions',
                  icon: Icons.flash_on,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        FilledButton.icon(
                          onPressed: () => _showRecordPaymentDialog(context, ref, payment),
                          icon: const Icon(Icons.check_circle, size: 18),
                          label: const Text('Record Payment'),
                          style: FilledButton.styleFrom(
                            backgroundColor: Colors.green,
                          ),
                        ),
                        if (payment.isOverdue && !payment.hasLateFee)
                          OutlinedButton.icon(
                            onPressed: () => _showApplyLateFeeDialog(context, ref, payment),
                            icon: const Icon(Icons.add_circle, size: 18),
                            label: const Text('Apply Late Fee'),
                          ),
                        OutlinedButton.icon(
                          onPressed: () {
                            // TODO: Send reminder
                          },
                          icon: const Icon(Icons.email, size: 18),
                          label: const Text('Send Reminder'),
                        ),
                      ],
                    ),
                  ],
                ),
              if (payment.status == PaymentStatus.pending)
                const SizedBox(height: 16),

              // Metadata
              Card(
                color: colorScheme.surfaceContainerLow,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Created: ${_formatDate(payment.createdAt)}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                      Text(
                        'Updated: ${_formatDate(payment.updatedAt)}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year}';
  }

  Future<bool?> _showDeleteDialog(BuildContext context, Payment payment) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Payment'),
        content: const Text(
          'Are you sure you want to delete this payment? This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  Future<void> _showRecordPaymentDialog(
    BuildContext context,
    WidgetRef ref,
    Payment payment,
  ) async {
    PaymentMethod? selectedMethod;
    final transactionIdController = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Record Payment'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Amount: ${payment.formattedTotalAmount}'),
            const SizedBox(height: 16),
            DropdownButtonFormField<PaymentMethod>(
              decoration: const InputDecoration(
                labelText: 'Payment Method *',
                border: OutlineInputBorder(),
              ),
              items: PaymentMethod.values.map((method) => DropdownMenuItem(
                    value: method,
                    child: Text(method.displayName),
                  )).toList(),
              onChanged: (value) => selectedMethod = value,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: transactionIdController,
              decoration: const InputDecoration(
                labelText: 'Transaction ID (optional)',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              if (selectedMethod == null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Please select a payment method'),
                    backgroundColor: Colors.red,
                  ),
                );
                return;
              }
              Navigator.of(context).pop(true);
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.green),
            child: const Text('Record'),
          ),
        ],
      ),
    );

    if (confirmed == true && selectedMethod != null && context.mounted) {
      final success = await ref.read(paymentsProvider.notifier).recordPayment(
            payment.id,
            DateTime.now(),
            selectedMethod!,
            transactionIdController.text.isNotEmpty
                ? transactionIdController.text
                : null,
          );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                success ? 'Payment recorded successfully' : 'Failed to record payment'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
        if (success) {
          ref.read(paymentDetailProvider(paymentId).notifier).refresh();
        }
      }
    }
  }

  Future<void> _showApplyLateFeeDialog(
    BuildContext context,
    WidgetRef ref,
    Payment payment,
  ) async {
    final feeController = TextEditingController(text: '50.00');

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Apply Late Fee'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Original Amount: ${payment.formattedAmount}'),
            Text('Overdue by ${payment.daysOverdue} days'),
            const SizedBox(height: 16),
            TextField(
              controller: feeController,
              decoration: const InputDecoration(
                labelText: 'Late Fee Amount *',
                border: OutlineInputBorder(),
                prefixText: '\$',
              ),
              keyboardType: TextInputType.number,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(backgroundColor: Colors.orange),
            child: const Text('Apply'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      final amount = double.parse(feeController.text);
      final success = await ref.read(paymentsProvider.notifier).applyLateFee(
            payment.id,
            amount,
          );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                success ? 'Late fee applied successfully' : 'Failed to apply late fee'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
        if (success) {
          ref.read(paymentDetailProvider(paymentId).notifier).refresh();
        }
      }
    }
  }

  Future<void> _showCancelDialog(
    BuildContext context,
    WidgetRef ref,
    Payment payment,
  ) async {
    final reasonController = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel Payment'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Are you sure you want to cancel this payment?'),
            const SizedBox(height: 16),
            TextField(
              controller: reasonController,
              decoration: const InputDecoration(
                labelText: 'Reason *',
                border: OutlineInputBorder(),
              ),
              maxLines: 2,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('No'),
          ),
          FilledButton(
            onPressed: () {
              if (reasonController.text.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Please provide a reason'),
                    backgroundColor: Colors.red,
                  ),
                );
                return;
              }
              Navigator.of(context).pop(true);
            },
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Cancel Payment'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      final success = await ref.read(paymentsProvider.notifier).cancelPayment(
            payment.id,
            reasonController.text,
          );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                success ? 'Payment cancelled' : 'Failed to cancel payment'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
        if (success) {
          ref.read(paymentDetailProvider(paymentId).notifier).refresh();
        }
      }
    }
  }

  Future<void> _showRefundDialog(
    BuildContext context,
    WidgetRef ref,
    Payment payment,
  ) async {
    final reasonController = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Refund Payment'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Refund Amount: ${payment.formattedTotalAmount}'),
            const SizedBox(height: 16),
            TextField(
              controller: reasonController,
              decoration: const InputDecoration(
                labelText: 'Reason *',
                border: OutlineInputBorder(),
              ),
              maxLines: 2,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              if (reasonController.text.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Please provide a reason'),
                    backgroundColor: Colors.red,
                  ),
                );
                return;
              }
              Navigator.of(context).pop(true);
            },
            style: FilledButton.styleFrom(
              backgroundColor: Colors.purple,
            ),
            child: const Text('Process Refund'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      final success = await ref.read(paymentsProvider.notifier).refundPayment(
            payment.id,
            reasonController.text,
          );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                success ? 'Refund processed' : 'Failed to process refund'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
        if (success) {
          ref.read(paymentDetailProvider(paymentId).notifier).refresh();
        }
      }
    }
  }
}

/// Status header with visual indicator
class _StatusHeader extends StatelessWidget {
  final Payment payment;

  const _StatusHeader({required this.payment});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    Color statusColor;
    IconData statusIcon;

    switch (payment.status) {
      case PaymentStatus.paid:
        statusColor = Colors.green;
        statusIcon = Icons.check_circle;
        break;
      case PaymentStatus.pending:
        statusColor = Colors.orange;
        statusIcon = Icons.pending;
        break;
      case PaymentStatus.partial:
        statusColor = Colors.blue;
        statusIcon = Icons.pie_chart;
        break;
      case PaymentStatus.overdue:
        statusColor = Colors.red;
        statusIcon = Icons.warning;
        break;
      case PaymentStatus.cancelled:
        statusColor = Colors.grey;
        statusIcon = Icons.cancel;
        break;
      case PaymentStatus.refunded:
        statusColor = Colors.purple;
        statusIcon = Icons.undo;
        break;
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Icon(statusIcon, color: statusColor, size: 40),
            ),
            const SizedBox(width: 24),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    payment.status.displayName,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: statusColor,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    payment.formattedTotalAmount,
                    style: theme.textTheme.titleLarge?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  if (payment.isOverdue && payment.status == PaymentStatus.pending) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.red.shade100,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'Overdue by ${payment.daysOverdue} days',
                        style: TextStyle(
                          color: Colors.red.shade800,
                          fontWeight: FontWeight.w500,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Section card with title and icon
class _SectionCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Widget> children;

  const _SectionCard({
    required this.title,
    required this.icon,
    required this.children,
  });

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
                Icon(icon, color: colorScheme.primary, size: 20),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            ...children,
          ],
        ),
      ),
    );
  }
}

/// Info row with icon, label and value
class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;
  final bool highlight;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
    this.valueColor,
    this.highlight = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: colorScheme.outline),
          const SizedBox(width: 12),
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: highlight ? FontWeight.bold : FontWeight.w500,
                fontSize: highlight ? 18 : null,
                color: valueColor,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
