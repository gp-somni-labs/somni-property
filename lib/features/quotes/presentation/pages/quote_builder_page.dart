import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/features/quotes/domain/entities/quote.dart';
import 'package:somni_property/features/quotes/domain/entities/quote_item.dart';
import 'package:somni_property/features/quotes/presentation/providers/quote_provider.dart';
import 'package:somni_property/features/quotes/presentation/widgets/quote_calculator_widget.dart';

/// Quote builder page for creating/editing quotes
class QuoteBuilderPage extends ConsumerStatefulWidget {
  final String? quoteId;

  const QuoteBuilderPage({super.key, this.quoteId});

  @override
  ConsumerState<QuoteBuilderPage> createState() => _QuoteBuilderPageState();
}

class _QuoteBuilderPageState extends ConsumerState<QuoteBuilderPage> {
  final _formKey = GlobalKey<FormState>();
  String? _clientId;
  String? _propertyId;
  double _taxRate = 8.5;
  int _validDays = 30;
  String? _notes;
  List<QuoteItem> _items = [];

  @override
  Widget build(BuildContext context) {
    final subtotal = Quote.calculateSubtotal(_items);
    final tax = Quote.calculateTax(subtotal, _taxRate);
    final total = Quote.calculateTotal(subtotal, tax);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.quoteId == null ? 'New Quote' : 'Edit Quote'),
        actions: [
          TextButton(
            onPressed: _saveAsDraft,
            child: const Text('Save Draft', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Client selection
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Client & Property',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 16),
                      DropdownButtonFormField<String>(
                        decoration: const InputDecoration(
                          labelText: 'Client',
                          hintText: 'Select a client',
                        ),
                        value: _clientId,
                        items: const [
                          DropdownMenuItem(value: '1', child: Text('John Doe')),
                          DropdownMenuItem(value: '2', child: Text('Jane Smith')),
                        ],
                        onChanged: (value) => setState(() => _clientId = value),
                        validator: (value) =>
                            value == null ? 'Please select a client' : null,
                      ),
                      const SizedBox(height: 16),
                      DropdownButtonFormField<String>(
                        decoration: const InputDecoration(
                          labelText: 'Property',
                          hintText: 'Select a property',
                        ),
                        value: _propertyId,
                        items: const [
                          DropdownMenuItem(
                              value: '1', child: Text('123 Main St')),
                          DropdownMenuItem(
                              value: '2', child: Text('456 Oak Ave')),
                        ],
                        onChanged: (value) => setState(() => _propertyId = value),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Line items
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'Line Items',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.add_circle),
                            onPressed: _addLineItem,
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      if (_items.isEmpty)
                        const Center(
                          child: Padding(
                            padding: EdgeInsets.all(32),
                            child: Text('No items yet. Add items to your quote.'),
                          ),
                        )
                      else
                        ..._items.asMap().entries.map((entry) {
                          final index = entry.key;
                          final item = entry.value;
                          return _buildLineItemRow(index, item);
                        }),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Calculator
              QuoteCalculatorWidget(
                subtotal: subtotal,
                taxRate: _taxRate,
                tax: tax,
                total: total,
                isEditable: true,
                onTaxRateChanged: (rate) {
                  setState(() => _taxRate = rate);
                },
              ),
              const SizedBox(height: 16),

              // Additional settings
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Additional Settings',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        initialValue: _validDays.toString(),
                        decoration: const InputDecoration(
                          labelText: 'Valid for (days)',
                          suffixText: 'days',
                        ),
                        keyboardType: TextInputType.number,
                        onChanged: (value) {
                          setState(() => _validDays = int.tryParse(value) ?? 30);
                        },
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        decoration: const InputDecoration(
                          labelText: 'Notes (optional)',
                          hintText: 'Add any notes or special instructions',
                        ),
                        maxLines: 3,
                        onChanged: (value) => _notes = value,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Action buttons
              ElevatedButton(
                onPressed: _sendQuote,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.all(16),
                ),
                child: const Text('Send to Client'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLineItemRow(int index, QuoteItem item) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: Text(item.description),
                ),
                Expanded(
                  child: Text('${item.quantity}x', textAlign: TextAlign.center),
                ),
                Expanded(
                  child: Text(item.formattedUnitPrice,
                      textAlign: TextAlign.center),
                ),
                Expanded(
                  child: Text(item.formattedTotal,
                      textAlign: TextAlign.right,
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                IconButton(
                  icon: const Icon(Icons.delete, size: 20),
                  onPressed: () => _removeLineItem(index),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _addLineItem() {
    showDialog(
      context: context,
      builder: (context) => _LineItemDialog(
        onAdd: (description, quantity, unitPrice) {
          setState(() {
            _items.add(
              QuoteItem(
                id: DateTime.now().millisecondsSinceEpoch.toString(),
                quoteId: widget.quoteId ?? '',
                description: description,
                quantity: quantity,
                unitPrice: unitPrice,
                total: QuoteItem.calculateTotal(quantity, unitPrice),
              ),
            );
          });
        },
      ),
    );
  }

  void _removeLineItem(int index) {
    setState(() {
      _items.removeAt(index);
    });
  }

  void _saveAsDraft() async {
    if (!_formKey.currentState!.validate()) return;

    try {
      // TODO: Implement save as draft
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Quote saved as draft')),
      );
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error saving quote: $e')),
      );
    }
  }

  void _sendQuote() async {
    if (!_formKey.currentState!.validate()) return;
    if (_items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please add at least one line item')),
      );
      return;
    }

    try {
      // TODO: Implement send quote
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Quote sent to client')),
      );
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error sending quote: $e')),
      );
    }
  }
}

class _LineItemDialog extends StatefulWidget {
  final Function(String description, double quantity, double unitPrice) onAdd;

  const _LineItemDialog({required this.onAdd});

  @override
  State<_LineItemDialog> createState() => _LineItemDialogState();
}

class _LineItemDialogState extends State<_LineItemDialog> {
  final _formKey = GlobalKey<FormState>();
  final _descriptionController = TextEditingController();
  final _quantityController = TextEditingController(text: '1');
  final _priceController = TextEditingController();

  @override
  void dispose() {
    _descriptionController.dispose();
    _quantityController.dispose();
    _priceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add Line Item'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              controller: _descriptionController,
              decoration: const InputDecoration(labelText: 'Description'),
              validator: (v) => v?.isEmpty == true ? 'Required' : null,
            ),
            TextFormField(
              controller: _quantityController,
              decoration: const InputDecoration(labelText: 'Quantity'),
              keyboardType: TextInputType.number,
              validator: (v) => v?.isEmpty == true ? 'Required' : null,
            ),
            TextFormField(
              controller: _priceController,
              decoration: const InputDecoration(
                  labelText: 'Unit Price', prefixText: '\$'),
              keyboardType: TextInputType.number,
              validator: (v) => v?.isEmpty == true ? 'Required' : null,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        TextButton(
          onPressed: () {
            if (_formKey.currentState!.validate()) {
              widget.onAdd(
                _descriptionController.text,
                double.parse(_quantityController.text),
                double.parse(_priceController.text),
              );
              Navigator.pop(context);
            }
          },
          child: const Text('Add'),
        ),
      ],
    );
  }
}
