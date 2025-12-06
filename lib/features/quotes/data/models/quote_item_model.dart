import 'package:somni_property/features/quotes/domain/entities/quote_item.dart';

/// Quote item model for JSON serialization
class QuoteItemModel extends QuoteItem {
  const QuoteItemModel({
    required super.id,
    required super.quoteId,
    super.productId,
    required super.description,
    required super.quantity,
    required super.unitPrice,
    required super.total,
    super.sortOrder = 0,
    super.notes,
    super.productName,
    super.productCategory,
    super.productSku,
  });

  /// Create model from JSON
  factory QuoteItemModel.fromJson(Map<String, dynamic> json) {
    return QuoteItemModel(
      id: json['id']?.toString() ?? '',
      quoteId: json['quote_id']?.toString() ?? json['quoteId']?.toString() ?? '',
      productId: json['product_id']?.toString() ?? json['productId']?.toString(),
      description: json['description']?.toString() ?? '',
      quantity: (json['quantity'] as num?)?.toDouble() ?? 1.0,
      unitPrice: (json['unit_price'] as num?)?.toDouble() ??
                 (json['unitPrice'] as num?)?.toDouble() ?? 0.0,
      total: (json['total'] as num?)?.toDouble() ?? 0.0,
      sortOrder: json['sort_order'] as int? ?? json['sortOrder'] as int? ?? 0,
      notes: json['notes']?.toString(),
      productName: json['product_name']?.toString() ?? json['productName']?.toString(),
      productCategory: json['product_category']?.toString() ??
                      json['productCategory']?.toString(),
      productSku: json['product_sku']?.toString() ?? json['productSku']?.toString(),
    );
  }

  /// Convert model to JSON for API requests
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'quote_id': quoteId,
      if (productId != null) 'product_id': productId,
      'description': description,
      'quantity': quantity,
      'unit_price': unitPrice,
      'total': total,
      'sort_order': sortOrder,
      if (notes != null) 'notes': notes,
    };
  }

  /// Create model from entity
  factory QuoteItemModel.fromEntity(QuoteItem item) {
    return QuoteItemModel(
      id: item.id,
      quoteId: item.quoteId,
      productId: item.productId,
      description: item.description,
      quantity: item.quantity,
      unitPrice: item.unitPrice,
      total: item.total,
      sortOrder: item.sortOrder,
      notes: item.notes,
      productName: item.productName,
      productCategory: item.productCategory,
      productSku: item.productSku,
    );
  }

  /// Convert to entity
  QuoteItem toEntity() {
    return QuoteItem(
      id: id,
      quoteId: quoteId,
      productId: productId,
      description: description,
      quantity: quantity,
      unitPrice: unitPrice,
      total: total,
      sortOrder: sortOrder,
      notes: notes,
      productName: productName,
      productCategory: productCategory,
      productSku: productSku,
    );
  }
}
