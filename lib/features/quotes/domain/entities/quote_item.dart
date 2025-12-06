import 'package:equatable/equatable.dart';

/// Quote item entity representing a line item in a quote
class QuoteItem extends Equatable {
  final String id;
  final String quoteId;
  final String? productId;
  final String description;
  final double quantity;
  final double unitPrice;
  final double total;
  final int sortOrder;
  final String? notes;

  // Product details (if linked to product)
  final String? productName;
  final String? productCategory;
  final String? productSku;

  const QuoteItem({
    required this.id,
    required this.quoteId,
    this.productId,
    required this.description,
    required this.quantity,
    required this.unitPrice,
    required this.total,
    this.sortOrder = 0,
    this.notes,
    this.productName,
    this.productCategory,
    this.productSku,
  });

  /// Calculate total from quantity and unit price
  static double calculateTotal(double quantity, double unitPrice) {
    return quantity * unitPrice;
  }

  /// Check if this is a custom item (not linked to product)
  bool get isCustomItem => productId == null;

  /// Get formatted unit price
  String get formattedUnitPrice => '\$${unitPrice.toStringAsFixed(2)}';

  /// Get formatted total
  String get formattedTotal => '\$${total.toStringAsFixed(2)}';

  /// Recalculate total based on quantity and unit price
  QuoteItem recalculate() {
    return copyWith(
      total: calculateTotal(quantity, unitPrice),
    );
  }

  /// Copy with new values
  QuoteItem copyWith({
    String? id,
    String? quoteId,
    String? productId,
    String? description,
    double? quantity,
    double? unitPrice,
    double? total,
    int? sortOrder,
    String? notes,
    String? productName,
    String? productCategory,
    String? productSku,
  }) {
    return QuoteItem(
      id: id ?? this.id,
      quoteId: quoteId ?? this.quoteId,
      productId: productId ?? this.productId,
      description: description ?? this.description,
      quantity: quantity ?? this.quantity,
      unitPrice: unitPrice ?? this.unitPrice,
      total: total ?? this.total,
      sortOrder: sortOrder ?? this.sortOrder,
      notes: notes ?? this.notes,
      productName: productName ?? this.productName,
      productCategory: productCategory ?? this.productCategory,
      productSku: productSku ?? this.productSku,
    );
  }

  @override
  List<Object?> get props => [
        id,
        quoteId,
        productId,
        description,
        quantity,
        unitPrice,
        total,
        sortOrder,
        notes,
      ];
}
