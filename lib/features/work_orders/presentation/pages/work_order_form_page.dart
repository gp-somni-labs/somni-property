import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/work_orders/domain/entities/work_order.dart';
import 'package:somni_property/features/work_orders/presentation/providers/work_order_provider.dart';

/// Form page for creating and editing work orders (maintenance requests)
class WorkOrderFormPage extends ConsumerStatefulWidget {
  final String? workOrderId;

  const WorkOrderFormPage({super.key, this.workOrderId});

  bool get isEditing => workOrderId != null;

  @override
  ConsumerState<WorkOrderFormPage> createState() => _WorkOrderFormPageState();
}

class _WorkOrderFormPageState extends ConsumerState<WorkOrderFormPage> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _unitNumberController = TextEditingController();
  final _estimatedCostController = TextEditingController();
  final _notesController = TextEditingController();

  WorkOrderCategory _selectedCategory = WorkOrderCategory.general;
  WorkOrderPriority _selectedPriority = WorkOrderPriority.medium;
  WorkOrderStatus _selectedStatus = WorkOrderStatus.open;
  DateTime? _scheduledDate;

  String? _unitId;
  String? _tenantId;
  String? _assignedTo;
  String? _assignedName;

  bool _isLoading = false;
  WorkOrder? _existingWorkOrder;

  @override
  void initState() {
    super.initState();
    if (widget.isEditing) {
      _loadWorkOrder();
    }
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    _unitNumberController.dispose();
    _estimatedCostController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _loadWorkOrder() async {
    setState(() => _isLoading = true);

    // Load from detail provider
    await Future.delayed(const Duration(milliseconds: 100));
    final detailState = ref.read(workOrderDetailProvider(widget.workOrderId!));

    if (detailState.workOrder != null) {
      _populateForm(detailState.workOrder!);
    }

    setState(() => _isLoading = false);
  }

  void _populateForm(WorkOrder workOrder) {
    _existingWorkOrder = workOrder;
    _titleController.text = workOrder.title;
    _descriptionController.text = workOrder.description;
    _unitNumberController.text = workOrder.unitNumber ?? '';
    _estimatedCostController.text = workOrder.estimatedCost?.toString() ?? '';
    _notesController.text = workOrder.notes ?? '';

    setState(() {
      _selectedCategory = workOrder.category;
      _selectedPriority = workOrder.priority;
      _selectedStatus = workOrder.status;
      _scheduledDate = workOrder.scheduledDate;
      _unitId = workOrder.unitId;
      _tenantId = workOrder.tenantId;
      _assignedTo = workOrder.assignedTo;
      _assignedName = workOrder.assignedName;
    });
  }

  Future<void> _submitForm() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() => _isLoading = true);

    final workOrder = WorkOrder(
      id: widget.workOrderId ?? '',
      unitId: _unitId,
      unitNumber: _unitNumberController.text.isNotEmpty
          ? _unitNumberController.text
          : null,
      tenantId: _tenantId,
      title: _titleController.text.trim(),
      description: _descriptionController.text.trim(),
      category: _selectedCategory,
      priority: _selectedPriority,
      status: _selectedStatus,
      scheduledDate: _scheduledDate,
      completedDate: _existingWorkOrder?.completedDate,
      assignedTo: _assignedTo,
      assignedName: _assignedName,
      estimatedCost: _estimatedCostController.text.isNotEmpty
          ? double.tryParse(_estimatedCostController.text)
          : null,
      actualCost: _existingWorkOrder?.actualCost,
      notes: _notesController.text.isNotEmpty ? _notesController.text : null,
      createdAt: _existingWorkOrder?.createdAt ?? DateTime.now(),
      updatedAt: DateTime.now(),
    );

    bool success;
    if (widget.isEditing) {
      success = await ref.read(workOrdersProvider.notifier).updateWorkOrder(workOrder);
    } else {
      success = await ref.read(workOrdersProvider.notifier).createWorkOrder(workOrder);
    }

    setState(() => _isLoading = false);

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.isEditing
                ? 'Work order updated successfully'
                : 'Work order created successfully'),
            backgroundColor: Colors.green,
          ),
        );
        context.pop();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.isEditing
                ? 'Failed to update work order'
                : 'Failed to create work order'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEditing ? 'Edit Work Order' : 'New Work Order'),
        actions: [
          if (_isLoading)
            const Center(
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: 16),
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
            )
          else
            TextButton(
              onPressed: _submitForm,
              child: const Text('Save'),
            ),
        ],
      ),
      body: _isLoading && widget.isEditing && _existingWorkOrder == null
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Basic Information Section
                    Text(
                      'Basic Information',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Title
                    TextFormField(
                      controller: _titleController,
                      decoration: const InputDecoration(
                        labelText: 'Title *',
                        hintText: 'Brief description of the issue',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.title),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Please enter a title';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Description
                    TextFormField(
                      controller: _descriptionController,
                      decoration: const InputDecoration(
                        labelText: 'Description *',
                        hintText: 'Detailed description of the maintenance issue',
                        border: OutlineInputBorder(),
                        alignLabelWithHint: true,
                      ),
                      maxLines: 4,
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Please enter a description';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Unit Number
                    TextFormField(
                      controller: _unitNumberController,
                      decoration: const InputDecoration(
                        labelText: 'Unit Number',
                        hintText: 'e.g., 101, A1',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.apartment),
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Classification Section
                    Text(
                      'Classification',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Category
                    DropdownButtonFormField<WorkOrderCategory>(
                      value: _selectedCategory,
                      decoration: const InputDecoration(
                        labelText: 'Category *',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.category),
                      ),
                      items: WorkOrderCategory.values
                          .map((category) => DropdownMenuItem(
                                value: category,
                                child: Row(
                                  children: [
                                    Icon(
                                      _getCategoryIcon(category),
                                      size: 20,
                                      color: _getCategoryColor(category),
                                    ),
                                    const SizedBox(width: 8),
                                    Text(category.displayName),
                                  ],
                                ),
                              ))
                          .toList(),
                      onChanged: (value) {
                        if (value != null) {
                          setState(() => _selectedCategory = value);
                        }
                      },
                    ),
                    const SizedBox(height: 16),

                    // Priority
                    DropdownButtonFormField<WorkOrderPriority>(
                      value: _selectedPriority,
                      decoration: const InputDecoration(
                        labelText: 'Priority *',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.flag),
                      ),
                      items: WorkOrderPriority.values
                          .map((priority) => DropdownMenuItem(
                                value: priority,
                                child: Row(
                                  children: [
                                    Icon(
                                      _getPriorityIcon(priority),
                                      size: 20,
                                      color: _getPriorityColor(priority),
                                    ),
                                    const SizedBox(width: 8),
                                    Text(priority.displayName),
                                  ],
                                ),
                              ))
                          .toList(),
                      onChanged: (value) {
                        if (value != null) {
                          setState(() => _selectedPriority = value);
                        }
                      },
                    ),
                    const SizedBox(height: 16),

                    // Status (only show for editing)
                    if (widget.isEditing) ...[
                      DropdownButtonFormField<WorkOrderStatus>(
                        value: _selectedStatus,
                        decoration: const InputDecoration(
                          labelText: 'Status',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.info),
                        ),
                        items: WorkOrderStatus.values
                            .map((status) => DropdownMenuItem(
                                  value: status,
                                  child: Text(status.displayName),
                                ))
                            .toList(),
                        onChanged: (value) {
                          if (value != null) {
                            setState(() => _selectedStatus = value);
                          }
                        },
                      ),
                      const SizedBox(height: 24),
                    ],

                    // Scheduling Section
                    Text(
                      'Scheduling',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Scheduled Date
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.event),
                      title: const Text('Scheduled Date'),
                      subtitle: Text(
                        _scheduledDate != null
                            ? '${_scheduledDate!.month}/${_scheduledDate!.day}/${_scheduledDate!.year}'
                            : 'Not scheduled',
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (_scheduledDate != null)
                            IconButton(
                              icon: const Icon(Icons.clear),
                              onPressed: () {
                                setState(() => _scheduledDate = null);
                              },
                            ),
                          IconButton(
                            icon: const Icon(Icons.calendar_today),
                            onPressed: _selectScheduledDate,
                          ),
                        ],
                      ),
                    ),
                    const Divider(),
                    const SizedBox(height: 16),

                    // Cost Section
                    Text(
                      'Cost Estimate',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Estimated Cost
                    TextFormField(
                      controller: _estimatedCostController,
                      decoration: const InputDecoration(
                        labelText: 'Estimated Cost',
                        hintText: '0.00',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.attach_money),
                        prefixText: '\$ ',
                      ),
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      validator: (value) {
                        if (value != null && value.isNotEmpty) {
                          if (double.tryParse(value) == null) {
                            return 'Please enter a valid amount';
                          }
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 24),

                    // Notes Section
                    Text(
                      'Additional Notes',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _notesController,
                      decoration: const InputDecoration(
                        labelText: 'Notes',
                        hintText: 'Any additional information or special instructions',
                        border: OutlineInputBorder(),
                        alignLabelWithHint: true,
                      ),
                      maxLines: 3,
                    ),
                    const SizedBox(height: 24),

                    // Priority Warning
                    if (_selectedPriority == WorkOrderPriority.urgent ||
                        _selectedPriority == WorkOrderPriority.emergency)
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: _selectedPriority == WorkOrderPriority.emergency
                              ? Colors.red.shade50
                              : Colors.orange.shade50,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: _selectedPriority == WorkOrderPriority.emergency
                                ? Colors.red.shade200
                                : Colors.orange.shade200,
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              _selectedPriority == WorkOrderPriority.emergency
                                  ? Icons.emergency
                                  : Icons.warning_amber,
                              color: _selectedPriority == WorkOrderPriority.emergency
                                  ? Colors.red
                                  : Colors.orange,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _selectedPriority == WorkOrderPriority.emergency
                                        ? 'Emergency Priority'
                                        : 'Urgent Priority',
                                    style: TextStyle(
                                      fontWeight: FontWeight.bold,
                                      color: _selectedPriority == WorkOrderPriority.emergency
                                          ? Colors.red.shade800
                                          : Colors.orange.shade800,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    _selectedPriority == WorkOrderPriority.emergency
                                        ? 'This will be flagged for immediate attention and notification will be sent to all available staff.'
                                        : 'This will be prioritized and staff will be notified.',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: _selectedPriority == WorkOrderPriority.emergency
                                          ? Colors.red.shade700
                                          : Colors.orange.shade700,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
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
                            : Icon(widget.isEditing ? Icons.save : Icons.add),
                        label: Text(widget.isEditing
                            ? 'Update Work Order'
                            : 'Create Work Order'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                ),
              ),
            ),
    );
  }

  Future<void> _selectScheduledDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _scheduledDate ?? DateTime.now(),
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 365 * 2)),
    );
    if (picked != null) {
      setState(() => _scheduledDate = picked);
    }
  }

  IconData _getCategoryIcon(WorkOrderCategory category) {
    switch (category) {
      case WorkOrderCategory.plumbing:
        return Icons.plumbing;
      case WorkOrderCategory.electrical:
        return Icons.electrical_services;
      case WorkOrderCategory.hvac:
        return Icons.ac_unit;
      case WorkOrderCategory.appliance:
        return Icons.kitchen;
      case WorkOrderCategory.structural:
        return Icons.foundation;
      case WorkOrderCategory.pest:
        return Icons.pest_control;
      case WorkOrderCategory.cleaning:
        return Icons.cleaning_services;
      case WorkOrderCategory.landscaping:
        return Icons.grass;
      case WorkOrderCategory.security:
        return Icons.security;
      case WorkOrderCategory.general:
      case WorkOrderCategory.other:
        return Icons.build;
    }
  }

  Color _getCategoryColor(WorkOrderCategory category) {
    switch (category) {
      case WorkOrderCategory.plumbing:
        return Colors.blue;
      case WorkOrderCategory.electrical:
        return Colors.amber;
      case WorkOrderCategory.hvac:
        return Colors.teal;
      case WorkOrderCategory.appliance:
        return Colors.purple;
      case WorkOrderCategory.structural:
        return Colors.brown;
      case WorkOrderCategory.pest:
        return Colors.orange;
      case WorkOrderCategory.cleaning:
        return Colors.cyan;
      case WorkOrderCategory.landscaping:
        return Colors.green;
      case WorkOrderCategory.security:
        return Colors.red;
      case WorkOrderCategory.general:
      case WorkOrderCategory.other:
        return Colors.grey;
    }
  }

  IconData _getPriorityIcon(WorkOrderPriority priority) {
    switch (priority) {
      case WorkOrderPriority.emergency:
        return Icons.emergency;
      case WorkOrderPriority.urgent:
        return Icons.priority_high;
      default:
        return Icons.flag;
    }
  }

  Color _getPriorityColor(WorkOrderPriority priority) {
    switch (priority) {
      case WorkOrderPriority.low:
        return Colors.green;
      case WorkOrderPriority.medium:
        return Colors.blue;
      case WorkOrderPriority.high:
        return Colors.orange;
      case WorkOrderPriority.urgent:
        return Colors.red;
      case WorkOrderPriority.emergency:
        return Colors.red.shade900;
    }
  }
}
