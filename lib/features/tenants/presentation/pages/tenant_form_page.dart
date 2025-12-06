import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/tenants/domain/entities/tenant.dart';
import 'package:somni_property/features/tenants/presentation/providers/tenant_provider.dart';

/// Page for creating or editing a tenant
class TenantFormPage extends ConsumerStatefulWidget {
  final String? tenantId;

  const TenantFormPage({super.key, this.tenantId});

  bool get isEditing => tenantId != null;

  @override
  ConsumerState<TenantFormPage> createState() => _TenantFormPageState();
}

class _TenantFormPageState extends ConsumerState<TenantFormPage> {
  final _formKey = GlobalKey<FormState>();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _dateOfBirthController = TextEditingController();
  final _notesController = TextEditingController();

  // Emergency contact
  final _emergencyNameController = TextEditingController();
  final _emergencyPhoneController = TextEditingController();
  final _emergencyRelationshipController = TextEditingController();

  TenantStatus _status = TenantStatus.active;
  bool _isLoading = false;
  bool _hasEmergencyContact = false;

  @override
  void initState() {
    super.initState();
    if (widget.isEditing) {
      _loadTenant();
    }
  }

  Future<void> _loadTenant() async {
    setState(() => _isLoading = true);

    final state = ref.read(tenantDetailProvider(widget.tenantId!));
    if (state.tenant != null) {
      _populateForm(state.tenant!);
    }

    setState(() => _isLoading = false);
  }

  void _populateForm(Tenant tenant) {
    _firstNameController.text = tenant.firstName;
    _lastNameController.text = tenant.lastName;
    _emailController.text = tenant.email;
    _phoneController.text = tenant.phone;
    _dateOfBirthController.text = tenant.dateOfBirth ?? '';
    _notesController.text = tenant.notes ?? '';
    _status = tenant.status;

    if (tenant.emergencyContact != null) {
      _hasEmergencyContact = true;
      _emergencyNameController.text = tenant.emergencyContact!.name;
      _emergencyPhoneController.text = tenant.emergencyContact!.phone;
      _emergencyRelationshipController.text =
          tenant.emergencyContact!.relationship;
    }
  }

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _dateOfBirthController.dispose();
    _notesController.dispose();
    _emergencyNameController.dispose();
    _emergencyPhoneController.dispose();
    _emergencyRelationshipController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEditing ? 'Edit Tenant' : 'New Tenant'),
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
                    // Basic Information
                    Text(
                      'Basic Information',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _firstNameController,
                            decoration: const InputDecoration(
                              labelText: 'First Name *',
                              border: OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'First name is required';
                              }
                              return null;
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: TextFormField(
                            controller: _lastNameController,
                            decoration: const InputDecoration(
                              labelText: 'Last Name *',
                              border: OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Last name is required';
                              }
                              return null;
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _emailController,
                      decoration: const InputDecoration(
                        labelText: 'Email *',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.email_outlined),
                      ),
                      keyboardType: TextInputType.emailAddress,
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Email is required';
                        }
                        if (!value.contains('@')) {
                          return 'Enter a valid email';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _phoneController,
                      decoration: const InputDecoration(
                        labelText: 'Phone *',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.phone_outlined),
                        hintText: '(555) 555-5555',
                      ),
                      keyboardType: TextInputType.phone,
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Phone is required';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _dateOfBirthController,
                      decoration: const InputDecoration(
                        labelText: 'Date of Birth',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.cake_outlined),
                        hintText: 'MM/DD/YYYY',
                      ),
                      readOnly: true,
                      onTap: () async {
                        final date = await showDatePicker(
                          context: context,
                          initialDate: DateTime(1990),
                          firstDate: DateTime(1900),
                          lastDate: DateTime.now(),
                        );
                        if (date != null) {
                          _dateOfBirthController.text =
                              '${date.month}/${date.day}/${date.year}';
                        }
                      },
                    ),
                    const SizedBox(height: 16),

                    DropdownButtonFormField<TenantStatus>(
                      value: _status,
                      decoration: const InputDecoration(
                        labelText: 'Status',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.flag_outlined),
                      ),
                      items: TenantStatus.values.map((status) {
                        return DropdownMenuItem(
                          value: status,
                          child: Text(status.displayName),
                        );
                      }).toList(),
                      onChanged: (value) {
                        if (value != null) {
                          setState(() => _status = value);
                        }
                      },
                    ),
                    const SizedBox(height: 24),

                    // Emergency Contact
                    Row(
                      children: [
                        Text(
                          'Emergency Contact',
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const Spacer(),
                        Switch(
                          value: _hasEmergencyContact,
                          onChanged: (value) {
                            setState(() => _hasEmergencyContact = value);
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    if (_hasEmergencyContact) ...[
                      TextFormField(
                        controller: _emergencyNameController,
                        decoration: const InputDecoration(
                          labelText: 'Contact Name',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.person_outline),
                        ),
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _emergencyPhoneController,
                        decoration: const InputDecoration(
                          labelText: 'Contact Phone',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.phone_outlined),
                        ),
                        keyboardType: TextInputType.phone,
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _emergencyRelationshipController,
                        decoration: const InputDecoration(
                          labelText: 'Relationship',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.people_outline),
                          hintText: 'e.g., Spouse, Parent, Sibling',
                        ),
                      ),
                      const SizedBox(height: 24),
                    ],

                    // Notes
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
                        border: OutlineInputBorder(),
                        alignLabelWithHint: true,
                      ),
                      maxLines: 4,
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
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() => _isLoading = true);

    final tenant = Tenant(
      id: widget.tenantId ?? '',
      firstName: _firstNameController.text.trim(),
      lastName: _lastNameController.text.trim(),
      email: _emailController.text.trim(),
      phone: _phoneController.text.replaceAll(RegExp(r'[^\d]'), ''),
      dateOfBirth: _dateOfBirthController.text.isNotEmpty
          ? _dateOfBirthController.text
          : null,
      emergencyContact: _hasEmergencyContact &&
              _emergencyNameController.text.isNotEmpty
          ? EmergencyContact(
              name: _emergencyNameController.text.trim(),
              phone: _emergencyPhoneController.text.replaceAll(RegExp(r'[^\d]'), ''),
              relationship: _emergencyRelationshipController.text.trim(),
            )
          : null,
      status: _status,
      notes: _notesController.text.isNotEmpty ? _notesController.text : null,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

    bool success;
    if (widget.isEditing) {
      success = await ref.read(tenantsProvider.notifier).updateTenant(tenant);
    } else {
      success = await ref.read(tenantsProvider.notifier).createTenant(tenant);
    }

    setState(() => _isLoading = false);

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.isEditing
                ? 'Tenant updated successfully'
                : 'Tenant created successfully'),
            backgroundColor: Colors.green,
          ),
        );
        context.pop();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.isEditing
                ? 'Failed to update tenant'
                : 'Failed to create tenant'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}
