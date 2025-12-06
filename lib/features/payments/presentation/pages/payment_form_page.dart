import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';
import 'package:somni_property/features/payments/presentation/providers/payment_provider.dart';

/// Page for creating or editing a payment
class PaymentFormPage extends ConsumerStatefulWidget {
  final String? paymentId;

  const PaymentFormPage({super.key, this.paymentId});

  bool get isEditing => paymentId != null;

  @override
  ConsumerState<PaymentFormPage> createState() => _PaymentFormPageState();
}

class _PaymentFormPageState extends ConsumerState<PaymentFormPage> {
  final _formKey = GlobalKey<FormState>();
  final _leaseIdController = TextEditingController();
  final _tenantIdController = TextEditingController();
  final _unitIdController = TextEditingController();
  final _amountController = TextEditingController();
  final _lateFeeController = TextEditingController();
  final _transactionIdController = TextEditingController();
  final _notesController = TextEditingController();

  DateTime _dueDate = DateTime.now().add(const Duration(days: 30));
  DateTime? _paidDate;
  PaymentStatus _status = PaymentStatus.pending;
  PaymentType _type = PaymentType.rent;
  PaymentMethod? _method;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    if (widget.isEditing) {
      _loadPayment();
    }
  }

  Future<void> _loadPayment() async {
    setState(() => _isLoading = true);

    final state = ref.read(paymentDetailProvider(widget.paymentId!));
    if (state.payment != null) {
      _populateForm(state.payment!);
    }

    setState(() => _isLoading = false);
  }

  void _populateForm(Payment payment) {
    _leaseIdController.text = payment.leaseId;
    _tenantIdController.text = payment.tenantId;
    _unitIdController.text = payment.unitId;
    _amountController.text = payment.amount.toString();
    if (payment.lateFee != null) {
      _lateFeeController.text = payment.lateFee.toString();
    }
    if (payment.transactionId != null) {
      _transactionIdController.text = payment.transactionId!;
    }
    _notesController.text = payment.notes ?? '';
    _dueDate = payment.dueDate;
    _paidDate = payment.paidDate;
    _status = payment.status;
    _type = payment.type;
    _method = payment.method;
  }

  @override
  void dispose() {
    _leaseIdController.dispose();
    _tenantIdController.dispose();
    _unitIdController.dispose();
    _amountController.dispose();
    _lateFeeController.dispose();
    _transactionIdController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEditing ? 'Edit Payment' : 'New Payment'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Payment Type
                    Text(
                      'Payment Type',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    DropdownButtonFormField<PaymentType>(
                      value: _type,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.category),
                      ),
                      items: PaymentType.values
                          .map((type) => DropdownMenuItem(
                                value: type,
                                child: Text(type.displayName),
                              ))
                          .toList(),
                      onChanged: (value) {
                        if (value != null) setState(() => _type = value);
                      },
                    ),
                    const SizedBox(height: 24),

                    // Associated Records
                    Text(
                      'Associated Records',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    // TODO: Replace with proper pickers
                    TextFormField(
                      controller: _leaseIdController,
                      decoration: const InputDecoration(
                        labelText: 'Lease ID *',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.description),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Lease is required';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _tenantIdController,
                            decoration: const InputDecoration(
                              labelText: 'Tenant ID *',
                              border: OutlineInputBorder(),
                              prefixIcon: Icon(Icons.person),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Required';
                              }
                              return null;
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: TextFormField(
                            controller: _unitIdController,
                            decoration: const InputDecoration(
                              labelText: 'Unit ID *',
                              border: OutlineInputBorder(),
                              prefixIcon: Icon(Icons.apartment),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Required';
                              }
                              return null;
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),

                    // Amount
                    Text(
                      'Amount Details',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          flex: 2,
                          child: TextFormField(
                            controller: _amountController,
                            decoration: const InputDecoration(
                              labelText: 'Amount *',
                              border: OutlineInputBorder(),
                              prefixText: '\$ ',
                            ),
                            keyboardType: TextInputType.number,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Required';
                              }
                              if (double.tryParse(value) == null) {
                                return 'Invalid amount';
                              }
                              return null;
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: TextFormField(
                            controller: _lateFeeController,
                            decoration: const InputDecoration(
                              labelText: 'Late Fee',
                              border: OutlineInputBorder(),
                              prefixText: '\$ ',
                            ),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),

                    // Dates
                    Text(
                      'Dates',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: _DatePickerField(
                            label: 'Due Date *',
                            value: _dueDate,
                            onChanged: (date) => setState(() => _dueDate = date),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: _DatePickerField(
                            label: 'Paid Date',
                            value: _paidDate,
                            optional: true,
                            onChanged: (date) => setState(() => _paidDate = date),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),

                    // Status & Method
                    Text(
                      'Status & Method',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<PaymentStatus>(
                            value: _status,
                            decoration: const InputDecoration(
                              labelText: 'Status',
                              border: OutlineInputBorder(),
                              prefixIcon: Icon(Icons.flag),
                            ),
                            items: PaymentStatus.values
                                .map((status) => DropdownMenuItem(
                                      value: status,
                                      child: Text(status.displayName),
                                    ))
                                .toList(),
                            onChanged: (value) {
                              if (value != null) setState(() => _status = value);
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: DropdownButtonFormField<PaymentMethod?>(
                            value: _method,
                            decoration: const InputDecoration(
                              labelText: 'Method',
                              border: OutlineInputBorder(),
                              prefixIcon: Icon(Icons.payment),
                            ),
                            items: [
                              const DropdownMenuItem(
                                value: null,
                                child: Text('Not Specified'),
                              ),
                              ...PaymentMethod.values
                                  .map((method) => DropdownMenuItem(
                                        value: method,
                                        child: Text(method.displayName),
                                      )),
                            ],
                            onChanged: (value) => setState(() => _method = value),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _transactionIdController,
                      decoration: const InputDecoration(
                        labelText: 'Transaction ID',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.receipt),
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Notes
                    Text(
                      'Notes',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _notesController,
                      decoration: const InputDecoration(
                        labelText: 'Notes',
                        border: OutlineInputBorder(),
                        alignLabelWithHint: true,
                      ),
                      maxLines: 3,
                    ),
                    const SizedBox(height: 32),

                    // Submit Button
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: _isLoading ? null : _submitForm,
                        icon: _isLoading
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.save),
                        label: Text(widget.isEditing ? 'Update' : 'Create'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                ),
              ),
            ),
    );
  }

  Future<void> _submitForm() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    final payment = Payment(
      id: widget.paymentId ?? '',
      leaseId: _leaseIdController.text.trim(),
      tenantId: _tenantIdController.text.trim(),
      unitId: _unitIdController.text.trim(),
      amount: double.parse(_amountController.text),
      dueDate: _dueDate,
      paidDate: _paidDate,
      status: _status,
      type: _type,
      method: _method,
      transactionId: _transactionIdController.text.isNotEmpty
          ? _transactionIdController.text
          : null,
      lateFee: _lateFeeController.text.isNotEmpty
          ? double.tryParse(_lateFeeController.text)
          : null,
      notes: _notesController.text.isNotEmpty ? _notesController.text : null,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

    bool success;
    if (widget.isEditing) {
      success = await ref.read(paymentsProvider.notifier).updatePayment(payment);
    } else {
      success = await ref.read(paymentsProvider.notifier).createPayment(payment);
    }

    setState(() => _isLoading = false);

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.isEditing
                ? 'Payment updated successfully'
                : 'Payment created successfully'),
            backgroundColor: Colors.green,
          ),
        );
        context.pop();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.isEditing
                ? 'Failed to update payment'
                : 'Failed to create payment'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}

/// Date picker field widget
class _DatePickerField extends StatelessWidget {
  final String label;
  final DateTime? value;
  final bool optional;
  final ValueChanged<DateTime> onChanged;

  const _DatePickerField({
    required this.label,
    required this.value,
    this.optional = false,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () async {
        final date = await showDatePicker(
          context: context,
          initialDate: value ?? DateTime.now(),
          firstDate: DateTime(2000),
          lastDate: DateTime(2100),
        );
        if (date != null) onChanged(date);
      },
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
          suffixIcon: const Icon(Icons.calendar_today),
        ),
        child: Text(
          value != null
              ? '${value!.month}/${value!.day}/${value!.year}'
              : optional
                  ? 'Not set'
                  : 'Select date',
          style: TextStyle(
            color: value == null ? Theme.of(context).hintColor : null,
          ),
        ),
      ),
    );
  }
}
