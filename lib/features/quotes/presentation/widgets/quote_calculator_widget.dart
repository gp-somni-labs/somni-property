import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Calculator widget for displaying and editing quote totals
class QuoteCalculatorWidget extends StatelessWidget {
  final double subtotal;
  final double taxRate;
  final double tax;
  final double total;
  final bool isEditable;
  final Function(double)? onTaxRateChanged;

  const QuoteCalculatorWidget({
    super.key,
    required this.subtotal,
    required this.taxRate,
    required this.tax,
    required this.total,
    this.isEditable = false,
    this.onTaxRateChanged,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Subtotal
            _buildCalculationRow(
              label: 'Subtotal',
              value: '\$${subtotal.toStringAsFixed(2)}',
              theme: theme,
            ),
            const SizedBox(height: 12),

            // Tax rate input
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Tax Rate',
                    style: theme.textTheme.bodyLarge,
                  ),
                ),
                if (isEditable) ...[
                  SizedBox(
                    width: 80,
                    child: TextField(
                      initialValue: taxRate.toStringAsFixed(2),
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      textAlign: TextAlign.right,
                      decoration: const InputDecoration(
                        isDense: true,
                        suffix: Text('%'),
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 8,
                        ),
                      ),
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,2}')),
                      ],
                      onChanged: (value) {
                        final rate = double.tryParse(value);
                        if (rate != null && onTaxRateChanged != null) {
                          onTaxRateChanged!(rate);
                        }
                      },
                    ),
                  ),
                ] else ...[
                  Text(
                    '${taxRate.toStringAsFixed(2)}%',
                    style: theme.textTheme.bodyLarge?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 12),

            // Tax amount
            _buildCalculationRow(
              label: 'Tax',
              value: '\$${tax.toStringAsFixed(2)}',
              theme: theme,
            ),
            const Divider(height: 24),

            // Total (prominent)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Total',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  '\$${total.toStringAsFixed(2)}',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: theme.colorScheme.primary,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCalculationRow({
    required String label,
    required String value,
    required ThemeData theme,
  }) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: theme.textTheme.bodyLarge,
        ),
        Text(
          value,
          style: theme.textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}
