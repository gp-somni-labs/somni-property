import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/features/quotes/presentation/providers/quote_provider.dart';
import 'package:somni_property/features/quotes/presentation/widgets/quote_status_badge.dart';
import 'package:somni_property/features/quotes/presentation/widgets/quote_calculator_widget.dart';

/// Quote detail page showing full quote information
class QuoteDetailPage extends ConsumerWidget {
  final String quoteId;

  const QuoteDetailPage({super.key, required this.quoteId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(quoteDetailProvider(quoteId));
    final theme = Theme.of(context);

    if (state.isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Quote Details')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (state.error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Quote Details')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 64, color: Colors.red),
              const SizedBox(height: 16),
              Text('Error: ${state.error}'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  ref.read(quoteDetailProvider(quoteId).notifier).loadQuote();
                },
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    final quote = state.quote;
    if (quote == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Quote Details')),
        body: const Center(child: Text('Quote not found')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Quote Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.download),
            onPressed: () => _downloadPdf(context, ref),
          ),
          PopupMenuButton(
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'duplicate', child: Text('Duplicate')),
              const PopupMenuItem(value: 'delete', child: Text('Delete')),
            ],
            onSelected: (value) => _handleMenuAction(context, ref, value),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          quote.clientName ?? 'Unknown Client',
                          style: theme.textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        QuoteStatusBadge(status: quote.status, showIcon: true),
                      ],
                    ),
                    if (quote.propertyAddress != null) ...[
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Icon(Icons.location_on,
                              size: 16, color: theme.colorScheme.onSurfaceVariant),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              quote.propertyAddress!,
                              style: theme.textTheme.bodyMedium,
                            ),
                          ),
                        ],
                      ),
                    ],
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: _buildInfoItem(
                            'Created',
                            _formatDate(quote.createdAt),
                            Icons.calendar_today,
                          ),
                        ),
                        if (quote.validUntil != null)
                          Expanded(
                            child: _buildInfoItem(
                              'Valid Until',
                              quote.formattedValidUntil!,
                              Icons.event,
                              isWarning: quote.isExpiringSoon,
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Line Items
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Line Items',
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                    ...quote.items.map((item) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Row(
                            children: [
                              Expanded(
                                flex: 3,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(item.description,
                                        style: theme.textTheme.bodyLarge),
                                    if (item.notes != null)
                                      Text(
                                        item.notes!,
                                        style: theme.textTheme.bodySmall
                                            ?.copyWith(
                                          color: theme
                                              .colorScheme.onSurfaceVariant,
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                              Expanded(
                                child: Text(
                                  '${item.quantity}x',
                                  textAlign: TextAlign.center,
                                ),
                              ),
                              Expanded(
                                child: Text(
                                  item.formattedUnitPrice,
                                  textAlign: TextAlign.center,
                                ),
                              ),
                              Expanded(
                                child: Text(
                                  item.formattedTotal,
                                  textAlign: TextAlign.right,
                                  style: const TextStyle(fontWeight: FontWeight.bold),
                                ),
                              ),
                            ],
                          ),
                        )),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Calculator
            QuoteCalculatorWidget(
              subtotal: quote.subtotal,
              taxRate: quote.taxRate,
              tax: quote.tax,
              total: quote.total,
              isEditable: false,
            ),
            const SizedBox(height: 16),

            // Notes
            if (quote.notes != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Notes',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(quote.notes!),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Action Buttons
            _buildActionButtons(context, ref, quote, state.isProcessing),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoItem(String label, String value, IconData icon,
      {bool isWarning = false}) {
    return Row(
      children: [
        Icon(icon,
            size: 16, color: isWarning ? Colors.red : Colors.grey),
        const SizedBox(width: 4),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label,
                  style: const TextStyle(
                      fontSize: 12, color: Colors.grey)),
              Text(value,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: isWarning ? Colors.red : null,
                  )),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildActionButtons(context, ref, quote, bool isProcessing) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (quote.status.name == 'draft')
          ElevatedButton.icon(
            onPressed: isProcessing ? null : () => _sendQuote(context, ref),
            icon: const Icon(Icons.send),
            label: const Text('Send to Client'),
          ),
        if (quote.status.name == 'sent' || quote.status.name == 'viewed') ...[
          ElevatedButton.icon(
            onPressed: isProcessing ? null : () => _approveQuote(context, ref),
            icon: const Icon(Icons.check),
            label: const Text('Approve Quote'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: isProcessing ? null : () => _declineQuote(context, ref),
            icon: const Icon(Icons.cancel),
            label: const Text('Decline Quote'),
          ),
        ],
      ],
    );
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year}';
  }

  void _sendQuote(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(quoteDetailProvider(quoteId).notifier).sendQuote();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Quote sent successfully')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error sending quote: $e')),
        );
      }
    }
  }

  void _approveQuote(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(quoteDetailProvider(quoteId).notifier).approveQuote();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Quote approved')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error approving quote: $e')),
        );
      }
    }
  }

  void _declineQuote(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(quoteDetailProvider(quoteId).notifier).declineQuote();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Quote declined')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error declining quote: $e')),
        );
      }
    }
  }

  void _downloadPdf(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(quoteDetailProvider(quoteId).notifier).generatePdf();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('PDF downloaded')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error generating PDF: $e')),
        );
      }
    }
  }

  void _handleMenuAction(BuildContext context, WidgetRef ref, String action) {
    switch (action) {
      case 'duplicate':
        _duplicateQuote(context, ref);
        break;
      case 'delete':
        _deleteQuote(context, ref);
        break;
    }
  }

  void _duplicateQuote(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(quoteDetailProvider(quoteId).notifier).duplicateQuote();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Quote duplicated')),
        );
        Navigator.pop(context);
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error duplicating quote: $e')),
        );
      }
    }
  }

  void _deleteQuote(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Quote'),
        content: const Text('Are you sure you want to delete this quote?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      try {
        await ref.read(quotesProvider.notifier).deleteQuote(quoteId);
        if (context.mounted) {
          Navigator.pop(context);
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error deleting quote: $e')),
          );
        }
      }
    }
  }
}
