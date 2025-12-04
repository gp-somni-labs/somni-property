import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/properties/domain/entities/property.dart';
import 'package:somni_property/features/properties/domain/repositories/property_repository.dart';
import 'package:somni_property/features/properties/presentation/providers/property_provider.dart';

/// Property form page for creating and editing properties
class PropertyFormPage extends ConsumerStatefulWidget {
  final String? propertyId; // null for create, non-null for edit

  const PropertyFormPage({super.key, this.propertyId});

  bool get isEditing => propertyId != null;

  @override
  ConsumerState<PropertyFormPage> createState() => _PropertyFormPageState();
}

class _PropertyFormPageState extends ConsumerState<PropertyFormPage> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _addressController = TextEditingController();
  final _cityController = TextEditingController();
  final _stateController = TextEditingController();
  final _zipController = TextEditingController();
  final _unitsController = TextEditingController();
  final _descriptionController = TextEditingController();

  PropertyType _selectedType = PropertyType.apartment;
  PropertyStatus _selectedStatus = PropertyStatus.active;
  bool _isLoading = false;
  bool _initialized = false;

  @override
  void dispose() {
    _nameController.dispose();
    _addressController.dispose();
    _cityController.dispose();
    _stateController.dispose();
    _zipController.dispose();
    _unitsController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  void _initializeFromProperty(Property property) {
    if (_initialized) return;
    _initialized = true;

    _nameController.text = property.name;
    _addressController.text = property.address;
    _cityController.text = property.city;
    _stateController.text = property.state;
    _zipController.text = property.zipCode;
    _unitsController.text = property.totalUnits.toString();
    _descriptionController.text = property.description ?? '';
    _selectedType = property.type;
    _selectedStatus = property.status;
  }

  @override
  Widget build(BuildContext context) {
    // If editing, load existing property
    if (widget.isEditing) {
      final propertyAsync = ref.watch(propertyByIdProvider(widget.propertyId!));
      return propertyAsync.when(
        loading: () => Scaffold(
          appBar: AppBar(title: const Text('Loading...')),
          body: const Center(child: CircularProgressIndicator()),
        ),
        error: (error, _) => Scaffold(
          appBar: AppBar(title: const Text('Error')),
          body: Center(child: Text('Error: $error')),
        ),
        data: (property) {
          if (property == null) {
            return Scaffold(
              appBar: AppBar(title: const Text('Not Found')),
              body: const Center(child: Text('Property not found')),
            );
          }
          _initializeFromProperty(property);
          return _buildForm(context, property);
        },
      );
    }

    return _buildForm(context, null);
  }

  Widget _buildForm(BuildContext context, Property? existingProperty) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEditing ? 'Edit Property' : 'New Property'),
        actions: [
          if (widget.isEditing)
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () => _confirmDelete(existingProperty!),
              tooltip: 'Delete Property',
            ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Basic Information Section
            _SectionHeader(title: 'Basic Information', icon: Icons.info_outline),
            const SizedBox(height: 8),

            // Property Name
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(
                labelText: 'Property Name *',
                hintText: 'e.g., Sunset Apartments',
                prefixIcon: Icon(Icons.home_work),
              ),
              textCapitalization: TextCapitalization.words,
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Property name is required';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),

            // Property Type
            DropdownButtonFormField<PropertyType>(
              value: _selectedType,
              decoration: const InputDecoration(
                labelText: 'Property Type *',
                prefixIcon: Icon(Icons.category),
              ),
              items: PropertyType.values.map((type) {
                return DropdownMenuItem(
                  value: type,
                  child: Text(type.displayName),
                );
              }).toList(),
              onChanged: (value) {
                if (value != null) {
                  setState(() => _selectedType = value);
                }
              },
            ),
            const SizedBox(height: 16),

            // Status (only for editing)
            if (widget.isEditing) ...[
              DropdownButtonFormField<PropertyStatus>(
                value: _selectedStatus,
                decoration: const InputDecoration(
                  labelText: 'Status',
                  prefixIcon: Icon(Icons.flag),
                ),
                items: PropertyStatus.values.map((status) {
                  return DropdownMenuItem(
                    value: status,
                    child: Text(status.displayName),
                  );
                }).toList(),
                onChanged: (value) {
                  if (value != null) {
                    setState(() => _selectedStatus = value);
                  }
                },
              ),
              const SizedBox(height: 16),
            ],

            // Total Units
            TextFormField(
              controller: _unitsController,
              decoration: const InputDecoration(
                labelText: 'Total Units *',
                hintText: 'e.g., 12',
                prefixIcon: Icon(Icons.door_front_door),
              ),
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Total units is required';
                }
                final units = int.tryParse(value);
                if (units == null || units < 1) {
                  return 'Must be at least 1 unit';
                }
                return null;
              },
            ),
            const SizedBox(height: 24),

            // Location Section
            _SectionHeader(title: 'Location', icon: Icons.location_on),
            const SizedBox(height: 8),

            // Address
            TextFormField(
              controller: _addressController,
              decoration: const InputDecoration(
                labelText: 'Street Address *',
                hintText: 'e.g., 123 Main Street',
                prefixIcon: Icon(Icons.home),
              ),
              textCapitalization: TextCapitalization.words,
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Address is required';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),

            // City and State row
            Row(
              children: [
                Expanded(
                  flex: 2,
                  child: TextFormField(
                    controller: _cityController,
                    decoration: const InputDecoration(
                      labelText: 'City *',
                      hintText: 'e.g., Austin',
                    ),
                    textCapitalization: TextCapitalization.words,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'City is required';
                      }
                      return null;
                    },
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: TextFormField(
                    controller: _stateController,
                    decoration: const InputDecoration(
                      labelText: 'State *',
                      hintText: 'TX',
                    ),
                    textCapitalization: TextCapitalization.characters,
                    inputFormatters: [
                      LengthLimitingTextInputFormatter(2),
                      FilteringTextInputFormatter.allow(RegExp(r'[A-Za-z]')),
                    ],
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Required';
                      }
                      if (value.length != 2) {
                        return '2 chars';
                      }
                      return null;
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // ZIP Code
            TextFormField(
              controller: _zipController,
              decoration: const InputDecoration(
                labelText: 'ZIP Code *',
                hintText: 'e.g., 78701',
                prefixIcon: Icon(Icons.pin_drop),
              ),
              keyboardType: TextInputType.number,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(5),
              ],
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'ZIP code is required';
                }
                if (value.length != 5) {
                  return 'Must be 5 digits';
                }
                return null;
              },
            ),
            const SizedBox(height: 24),

            // Description Section
            _SectionHeader(title: 'Description', icon: Icons.description),
            const SizedBox(height: 8),

            TextFormField(
              controller: _descriptionController,
              decoration: const InputDecoration(
                labelText: 'Description (optional)',
                hintText: 'Enter property description...',
                alignLabelWithHint: true,
              ),
              maxLines: 4,
              textCapitalization: TextCapitalization.sentences,
            ),
            const SizedBox(height: 32),

            // Submit button
            FilledButton.icon(
              onPressed: _isLoading ? null : _submitForm,
              icon: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(widget.isEditing ? Icons.save : Icons.add),
              label: Text(widget.isEditing ? 'Save Changes' : 'Create Property'),
              style: FilledButton.styleFrom(
                minimumSize: const Size(double.infinity, 56),
              ),
            ),
            const SizedBox(height: 16),

            // Cancel button
            OutlinedButton(
              onPressed: _isLoading ? null : () => context.pop(),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size(double.infinity, 56),
              ),
              child: const Text('Cancel'),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Future<void> _submitForm() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      bool success;

      if (widget.isEditing) {
        // Update existing property
        final params = UpdatePropertyParams(
          name: _nameController.text.trim(),
          address: _addressController.text.trim(),
          city: _cityController.text.trim(),
          state: _stateController.text.trim().toUpperCase(),
          zipCode: _zipController.text.trim(),
          type: _selectedType,
          status: _selectedStatus,
          totalUnits: int.parse(_unitsController.text),
          description: _descriptionController.text.trim().isEmpty
              ? null
              : _descriptionController.text.trim(),
        );
        success = await ref
            .read(propertiesProvider.notifier)
            .updateProperty(widget.propertyId!, params);
      } else {
        // Create new property
        final params = CreatePropertyParams(
          name: _nameController.text.trim(),
          address: _addressController.text.trim(),
          city: _cityController.text.trim(),
          state: _stateController.text.trim().toUpperCase(),
          zipCode: _zipController.text.trim(),
          type: _selectedType,
          totalUnits: int.parse(_unitsController.text),
          description: _descriptionController.text.trim().isEmpty
              ? null
              : _descriptionController.text.trim(),
        );
        success =
            await ref.read(propertiesProvider.notifier).createProperty(params);
      }

      if (mounted) {
        if (success) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(widget.isEditing
                  ? 'Property updated successfully'
                  : 'Property created successfully'),
            ),
          );
          context.go('/properties');
        } else {
          final error = ref.read(propertiesProvider).error;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(error ?? 'An error occurred'),
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
          );
        }
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _confirmDelete(Property property) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Property'),
        content: Text(
          'Are you sure you want to delete "${property.name}"?\n\n'
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      setState(() => _isLoading = true);
      final success = await ref
          .read(propertiesProvider.notifier)
          .deleteProperty(property.id);

      if (mounted) {
        if (success) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('${property.name} deleted')),
          );
          context.go('/properties');
        } else {
          setState(() => _isLoading = false);
        }
      }
    }
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final IconData icon;

  const _SectionHeader({required this.title, required this.icon});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      children: [
        Icon(icon, size: 20, color: theme.colorScheme.primary),
        const SizedBox(width: 8),
        Text(
          title,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
            color: theme.colorScheme.primary,
          ),
        ),
      ],
    );
  }
}
