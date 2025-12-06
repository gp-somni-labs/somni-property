import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/leases/domain/entities/lease.dart';
import 'package:somni_property/features/leases/presentation/providers/lease_provider.dart';

/// Page for creating or editing a lease
class LeaseFormPage extends ConsumerStatefulWidget {
  final String? leaseId;

  const LeaseFormPage({super.key, this.leaseId});

  bool get isEditing => leaseId != null;

  @override
  ConsumerState<LeaseFormPage> createState() => _LeaseFormPageState();
}

class _LeaseFormPageState extends ConsumerState<LeaseFormPage> {
  final _formKey = GlobalKey<FormState>();
  final _unitIdController = TextEditingController();
  final _tenantIdController = TextEditingController();
  final _monthlyRentController = TextEditingController();
  final _securityDepositController = TextEditingController();
  final _termsController = TextEditingController();
  final _notesController = TextEditingController();

  DateTime _startDate = DateTime.now();
  DateTime _endDate = DateTime.now().add(const Duration(days: 365));
  LeaseStatus _status = LeaseStatus.pending;
  final List<String> _specialConditions = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    if (widget.isEditing) {
      _loadLease();
    }
  }

  Future<void> _loadLease() async {
    setState(() => _isLoading = true);

    final state = ref.read(leaseDetailProvider(widget.leaseId!));
    if (state.lease != null) {
      _populateForm(state.lease!);
    }

    setState(() => _isLoading = false);
  }

  void _populateForm(Lease lease) {
    _unitIdController.text = lease.unitId;
    _tenantIdController.text = lease.tenantId;
    _monthlyRentController.text = lease.monthlyRent.toString();
    _securityDepositController.text = lease.securityDeposit.toString();
    _termsController.text = lease.terms ?? '';
    _notesController.text = lease.notes ?? '';
    _startDate = lease.startDate;
    _endDate = lease.endDate;
    _status = lease.status;
    if (lease.specialConditions != null) {
      _specialConditions.addAll(lease.specialConditions!);
    }
  }

  @override
  void dispose() {
    _unitIdController.dispose();
    _tenantIdController.dispose();
    _monthlyRentController.dispose();
    _securityDepositController.dispose();
    _termsController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEditing ? 'Edit Lease' : 'New Lease'),
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
                    // Unit & Tenant Selection
                    Text(
                      'Unit & Tenant',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    // TODO: Replace with proper unit/tenant pickers
                    TextFormField(
                      controller: _unitIdController,
                      decoration: const InputDecoration(
                        labelText: 'Unit ID *',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.apartment),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Unit is required';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _tenantIdController,
                      decoration: const InputDecoration(
                        labelText: 'Tenant ID *',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.person),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Tenant is required';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 24),

                    // Lease Dates
                    Text(
                      'Lease Period',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: _DatePickerField(
                            label: 'Start Date *',
                            value: _startDate,
                            onChanged: (date) {
                              setState(() => _startDate = date);
                              // Auto-adjust end date if needed
                              if (_endDate.isBefore(_startDate)) {
                                _endDate = _startDate.add(const Duration(days: 365));
                              }
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: _DatePickerField(
                            label: 'End Date *',
                            value: _endDate,
                            firstDate: _startDate,
                            onChanged: (date) => setState(() => _endDate = date),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Duration: ${_endDate.difference(_startDate).inDays ~/ 30} months',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Financial Details
                    Text(
                      'Financial Details',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _monthlyRentController,
                            decoration: const InputDecoration(
                              labelText: 'Monthly Rent *',
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
                            controller: _securityDepositController,
                            decoration: const InputDecoration(
                              labelText: 'Security Deposit',
                              border: OutlineInputBorder(),
                              prefixText: '\$ ',
                            ),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),

                    // Status
                    Text(
                      'Status',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    DropdownButtonFormField<LeaseStatus>(
                      value: _status,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.flag),
                      ),
                      items: LeaseStatus.values
                          .map((status) => DropdownMenuItem(
                                value: status,
                                child: Text(status.displayName),
                              ))
                          .toList(),
                      onChanged: (value) {
                        if (value != null) setState(() => _status = value);
                      },
                    ),
                    const SizedBox(height: 24),

                    // Special Conditions
                    Text(
                      'Special Conditions',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ..._specialConditions.asMap().entries.map(
                          (entry) => ListTile(
                            dense: true,
                            leading: const Icon(Icons.check_circle, size: 20),
                            title: Text(entry.value),
                            trailing: IconButton(
                              icon: const Icon(Icons.remove_circle_outline),
                              onPressed: () {
                                setState(() => _specialConditions.removeAt(entry.key));
                              },
                            ),
                          ),
                        ),
                    TextButton.icon(
                      onPressed: () => _addSpecialCondition(context),
                      icon: const Icon(Icons.add),
                      label: const Text('Add Condition'),
                    ),
                    const SizedBox(height: 24),

                    // Terms & Notes
                    Text(
                      'Terms & Notes',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _termsController,
                      decoration: const InputDecoration(
                        labelText: 'Lease Terms',
                        border: OutlineInputBorder(),
                        alignLabelWithHint: true,
                      ),
                      maxLines: 4,
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

  Future<void> _addSpecialCondition(BuildContext context) async {
    final controller = TextEditingController();
    final condition = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add Condition'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            hintText: 'Enter special condition',
            border: OutlineInputBorder(),
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(controller.text),
            child: const Text('Add'),
          ),
        ],
      ),
    );

    if (condition != null && condition.isNotEmpty) {
      setState(() => _specialConditions.add(condition));
    }
  }

  Future<void> _submitForm() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    final lease = Lease(
      id: widget.leaseId ?? '',
      unitId: _unitIdController.text.trim(),
      tenantId: _tenantIdController.text.trim(),
      startDate: _startDate,
      endDate: _endDate,
      monthlyRent: double.parse(_monthlyRentController.text),
      securityDeposit: double.tryParse(_securityDepositController.text) ?? 0.0,
      status: _status,
      terms: _termsController.text.isNotEmpty ? _termsController.text : null,
      specialConditions: _specialConditions.isNotEmpty ? _specialConditions : null,
      notes: _notesController.text.isNotEmpty ? _notesController.text : null,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

    bool success;
    if (widget.isEditing) {
      success = await ref.read(leasesProvider.notifier).updateLease(lease);
    } else {
      success = await ref.read(leasesProvider.notifier).createLease(lease);
    }

    setState(() => _isLoading = false);

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.isEditing
                ? 'Lease updated successfully'
                : 'Lease created successfully'),
            backgroundColor: Colors.green,
          ),
        );
        context.pop();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.isEditing
                ? 'Failed to update lease'
                : 'Failed to create lease'),
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
  final DateTime value;
  final DateTime? firstDate;
  final ValueChanged<DateTime> onChanged;

  const _DatePickerField({
    required this.label,
    required this.value,
    this.firstDate,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () async {
        final date = await showDatePicker(
          context: context,
          initialDate: value,
          firstDate: firstDate ?? DateTime(2000),
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
        child: Text('${value.month}/${value.day}/${value.year}'),
      ),
    );
  }
}
