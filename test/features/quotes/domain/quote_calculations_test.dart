import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/features/quotes/domain/entities/quote.dart';
import 'package:somni_property/features/quotes/domain/entities/quote_item.dart';

void main() {
  group('Quote Calculations', () {
    test('calculateSubtotal should sum all item totals', () {
      final items = [
        QuoteItem(
          id: '1',
          quoteId: 'q1',
          description: 'Item 1',
          quantity: 2,
          unitPrice: 10.0,
          total: 20.0,
        ),
        QuoteItem(
          id: '2',
          quoteId: 'q1',
          description: 'Item 2',
          quantity: 3,
          unitPrice: 15.0,
          total: 45.0,
        ),
      ];

      final subtotal = Quote.calculateSubtotal(items);

      expect(subtotal, equals(65.0));
    });

    test('calculateTax should compute correct tax amount', () {
      final subtotal = 100.0;
      final taxRate = 8.5;

      final tax = Quote.calculateTax(subtotal, taxRate);

      expect(tax, equals(8.5));
    });

    test('calculateTax with zero rate should return zero', () {
      final subtotal = 100.0;
      final taxRate = 0.0;

      final tax = Quote.calculateTax(subtotal, taxRate);

      expect(tax, equals(0.0));
    });

    test('calculateTotal should sum subtotal and tax', () {
      final subtotal = 100.0;
      final tax = 8.5;

      final total = Quote.calculateTotal(subtotal, tax);

      expect(total, equals(108.5));
    });

    test('recalculate should update all amounts based on items', () {
      final items = [
        QuoteItem(
          id: '1',
          quoteId: 'q1',
          description: 'Item 1',
          quantity: 2,
          unitPrice: 10.0,
          total: 20.0,
        ),
      ];

      final quote = Quote(
        id: 'q1',
        status: QuoteStatus.draft,
        items: items,
        subtotal: 0.0, // Incorrect value
        taxRate: 10.0,
        tax: 0.0, // Incorrect value
        total: 0.0, // Incorrect value
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      final recalculated = quote.recalculate();

      expect(recalculated.subtotal, equals(20.0));
      expect(recalculated.tax, equals(2.0));
      expect(recalculated.total, equals(22.0));
    });
  });

  group('QuoteItem Calculations', () {
    test('calculateTotal should multiply quantity by unit price', () {
      final total = QuoteItem.calculateTotal(5, 12.50);

      expect(total, equals(62.5));
    });

    test('calculateTotal with decimal quantity', () {
      final total = QuoteItem.calculateTotal(2.5, 10.0);

      expect(total, equals(25.0));
    });

    test('recalculate should update item total', () {
      final item = QuoteItem(
        id: '1',
        quoteId: 'q1',
        description: 'Test Item',
        quantity: 3,
        unitPrice: 15.0,
        total: 0.0, // Incorrect value
      );

      final recalculated = item.recalculate();

      expect(recalculated.total, equals(45.0));
    });
  });

  group('Quote Status Logic', () {
    test('isExpired should return true for past date', () {
      final quote = Quote(
        id: 'q1',
        status: QuoteStatus.sent,
        items: [],
        subtotal: 0,
        taxRate: 0,
        tax: 0,
        total: 0,
        validUntil: DateTime.now().subtract(const Duration(days: 1)),
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      expect(quote.isExpired, isTrue);
    });

    test('isExpired should return false for future date', () {
      final quote = Quote(
        id: 'q1',
        status: QuoteStatus.sent,
        items: [],
        subtotal: 0,
        taxRate: 0,
        tax: 0,
        total: 0,
        validUntil: DateTime.now().add(const Duration(days: 30)),
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      expect(quote.isExpired, isFalse);
    });

    test('isExpiringSoon should return true within 3 days', () {
      final quote = Quote(
        id: 'q1',
        status: QuoteStatus.sent,
        items: [],
        subtotal: 0,
        taxRate: 0,
        tax: 0,
        total: 0,
        validUntil: DateTime.now().add(const Duration(days: 2)),
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      expect(quote.isExpiringSoon, isTrue);
    });

    test('isExpiringSoon should return false for more than 3 days', () {
      final quote = Quote(
        id: 'q1',
        status: QuoteStatus.sent,
        items: [],
        subtotal: 0,
        taxRate: 0,
        tax: 0,
        total: 0,
        validUntil: DateTime.now().add(const Duration(days: 10)),
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      expect(quote.isExpiringSoon, isFalse);
    });
  });

  group('Formatted Values', () {
    test('formattedSubtotal should format with 2 decimal places', () {
      final quote = Quote(
        id: 'q1',
        status: QuoteStatus.draft,
        items: [],
        subtotal: 1234.56,
        taxRate: 0,
        tax: 0,
        total: 0,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      expect(quote.formattedSubtotal, equals('\$1234.56'));
    });

    test('formattedTax should format with 2 decimal places', () {
      final quote = Quote(
        id: 'q1',
        status: QuoteStatus.draft,
        items: [],
        subtotal: 0,
        taxRate: 8.5,
        tax: 104.88,
        total: 0,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      expect(quote.formattedTax, equals('\$104.88'));
    });

    test('formattedTotal should format with 2 decimal places', () {
      final quote = Quote(
        id: 'q1',
        status: QuoteStatus.draft,
        items: [],
        subtotal: 0,
        taxRate: 0,
        tax: 0,
        total: 1339.44,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      expect(quote.formattedTotal, equals('\$1339.44'));
    });
  });
}
