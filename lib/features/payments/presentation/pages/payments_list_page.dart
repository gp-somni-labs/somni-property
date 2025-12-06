import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';
import 'package:somni_property/features/payments/presentation/providers/payment_provider.dart';
import 'package:somni_property/features/payments/presentation/widgets/payment_card.dart';

/// Page displaying list of all payments
class PaymentsListPage extends ConsumerStatefulWidget {
  const PaymentsListPage({super.key});

  @override
  ConsumerState<PaymentsListPage> createState() => _PaymentsListPageState();
}

class _PaymentsListPageState extends ConsumerState<PaymentsListPage> {
  PaymentStatus? _selectedStatus;
  PaymentType? _selectedType;
  bool _showOverdueOnly = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(paymentsProvider.notifier).loadPayments();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(paymentsProvider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Payments'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(paymentsProvider.notifier).loadPayments(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/payments/new'),
        icon: const Icon(Icons.add),
        label: const Text('New Payment'),
      ),
      body: Column(
        children: [
          // Stats Cards
          if (state.stats != null)
            SizedBox(
              height: 120,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.all(16),
                children: [
                  SizedBox(
                    width: 140,
                    child: PaymentStatsCard(
                      title: 'Total',
                      value: '\$${state.stats!.totalAmountDue.toStringAsFixed(0)}',
                      icon: Icons.payments,
                      color: colorScheme.primary,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: PaymentStatsCard(
                      title: 'Collected',
                      value: '\$${state.stats!.totalAmountPaid.toStringAsFixed(0)}',
                      icon: Icons.check_circle,
                      color: Colors.green,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: PaymentStatsCard(
                      title: 'Pending',
                      value: state.stats!.pendingPayments.toString(),
                      icon: Icons.pending,
                      color: Colors.orange,
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 140,
                    child: PaymentStatsCard(
                      title: 'Overdue',
                      value: '\$${state.stats!.totalOverdue.toStringAsFixed(0)}',
                      icon: Icons.warning,
                      color: Colors.red,
                    ),
                  ),
                ],
              ),
            ),

          // Filters
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                Row(
                  children: [
                    // Status Filter
                    Expanded(
                      child: DropdownButtonFormField<PaymentStatus?>(
                        value: _selectedStatus,
                        decoration: InputDecoration(
                          labelText: 'Status',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 12,
                          ),
                        ),
                        items: [
                          const DropdownMenuItem(
                            value: null,
                            child: Text('All Statuses'),
                          ),
                          ...PaymentStatus.values.map((status) => DropdownMenuItem(
                                value: status,
                                child: Text(status.displayName),
                              )),
                        ],
                        onChanged: (status) {
                          setState(() {
                            _selectedStatus = status;
                            _showOverdueOnly = false;
                          });
                          if (status == null) {
                            ref.read(paymentsProvider.notifier).loadPayments();
                          } else {
                            ref.read(paymentsProvider.notifier).filterByStatus(status);
                          }
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    // Type Filter
                    Expanded(
                      child: DropdownButtonFormField<PaymentType?>(
                        value: _selectedType,
                        decoration: InputDecoration(
                          labelText: 'Type',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 12,
                          ),
                        ),
                        items: [
                          const DropdownMenuItem(
                            value: null,
                            child: Text('All Types'),
                          ),
                          ...PaymentType.values.map((type) => DropdownMenuItem(
                                value: type,
                                child: Text(type.displayName),
                              )),
                        ],
                        onChanged: (type) {
                          setState(() {
                            _selectedType = type;
                          });
                          ref.read(paymentsProvider.notifier).loadPayments(
                                type: type,
                                status: _selectedStatus,
                              );
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    // Overdue Filter
                    FilterChip(
                      label: const Text('Overdue'),
                      selected: _showOverdueOnly,
                      avatar: _showOverdueOnly
                          ? null
                          : const Icon(Icons.warning_amber, size: 18),
                      onSelected: (selected) {
                        setState(() {
                          _showOverdueOnly = selected;
                          _selectedStatus = null;
                          _selectedType = null;
                        });
                        if (selected) {
                          ref.read(paymentsProvider.notifier).loadOverduePayments();
                        } else {
                          ref.read(paymentsProvider.notifier).loadPayments();
                        }
                      },
                    ),
                    const SizedBox(width: 8),
                    FilterChip(
                      label: const Text('Due Soon'),
                      selected: false,
                      avatar: const Icon(Icons.schedule, size: 18),
                      onSelected: (selected) {
                        setState(() {
                          _showOverdueOnly = false;
                          _selectedStatus = null;
                          _selectedType = null;
                        });
                        if (selected) {
                          ref.read(paymentsProvider.notifier).loadUpcomingPayments();
                        } else {
                          ref.read(paymentsProvider.notifier).loadPayments();
                        }
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Payments List
          Expanded(
            child: _buildPaymentsList(state),
          ),
        ],
      ),
    );
  }

  Widget _buildPaymentsList(PaymentsState state) {
    if (state.isLoading && state.payments.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.payments.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Error loading payments',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(state.error!),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => ref.read(paymentsProvider.notifier).loadPayments(),
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.payments.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.payments_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text(
              'No payments found',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text('Create your first payment to get started'),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => context.push('/payments/new'),
              icon: const Icon(Icons.add),
              label: const Text('New Payment'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(paymentsProvider.notifier).loadPayments(),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: state.payments.length,
        itemBuilder: (context, index) {
          final payment = state.payments[index];
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: PaymentCard(
              payment: payment,
              onTap: () => context.push('/payments/${payment.id}'),
              onRecord: payment.status == PaymentStatus.pending
                  ? () => _showRecordPaymentDialog(payment)
                  : null,
              onApplyLateFee: payment.isOverdue && !payment.hasLateFee
                  ? () => _showApplyLateFeeDialog(payment)
                  : null,
            ),
          );
        },
      ),
    );
  }

  Future<void> _showRecordPaymentDialog(Payment payment) async {
    PaymentMethod? selectedMethod;
    final transactionIdController = TextEditingController();
    DateTime paidDate = DateTime.now();

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

    if (confirmed == true && selectedMethod != null && mounted) {
      final success = await ref.read(paymentsProvider.notifier).recordPayment(
            payment.id,
            paidDate,
            selectedMethod!,
            transactionIdController.text.isNotEmpty
                ? transactionIdController.text
                : null,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                success ? 'Payment recorded successfully' : 'Failed to record payment'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _showApplyLateFeeDialog(Payment payment) async {
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
            onPressed: () {
              if (feeController.text.isEmpty ||
                  double.tryParse(feeController.text) == null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Please enter a valid amount'),
                    backgroundColor: Colors.red,
                  ),
                );
                return;
              }
              Navigator.of(context).pop(true);
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.orange),
            child: const Text('Apply'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final amount = double.parse(feeController.text);
      final success = await ref.read(paymentsProvider.notifier).applyLateFee(
            payment.id,
            amount,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                success ? 'Late fee applied successfully' : 'Failed to apply late fee'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    }
  }
}
