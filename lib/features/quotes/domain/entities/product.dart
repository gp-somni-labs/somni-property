import 'package:equatable/equatable.dart';

/// Product entity for quote product catalog
class Product extends Equatable {
  final String id;
  final String name;
  final String? description;
  final ProductCategory category;
  final double basePrice;
  final String? sku;
  final String? unit; // e.g., "each", "sq ft", "hour"
  final bool isActive;
  final List<VendorPrice> vendorPrices;
  final DateTime createdAt;
  final DateTime updatedAt;

  const Product({
    required this.id,
    required this.name,
    this.description,
    required this.category,
    required this.basePrice,
    this.sku,
    this.unit,
    this.isActive = true,
    this.vendorPrices = const [],
    required this.createdAt,
    required this.updatedAt,
  });

  /// Get lowest vendor price
  double? get lowestVendorPrice {
    if (vendorPrices.isEmpty) return null;
    return vendorPrices.map((v) => v.price).reduce((a, b) => a < b ? a : b);
  }

  /// Get formatted base price
  String get formattedBasePrice => '\$${basePrice.toStringAsFixed(2)}';

  /// Get formatted lowest vendor price
  String? get formattedLowestVendorPrice {
    final price = lowestVendorPrice;
    return price != null ? '\$${price.toStringAsFixed(2)}' : null;
  }

  /// Copy with new values
  Product copyWith({
    String? id,
    String? name,
    String? description,
    ProductCategory? category,
    double? basePrice,
    String? sku,
    String? unit,
    bool? isActive,
    List<VendorPrice>? vendorPrices,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Product(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      category: category ?? this.category,
      basePrice: basePrice ?? this.basePrice,
      sku: sku ?? this.sku,
      unit: unit ?? this.unit,
      isActive: isActive ?? this.isActive,
      vendorPrices: vendorPrices ?? this.vendorPrices,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  List<Object?> get props => [
        id,
        name,
        description,
        category,
        basePrice,
        sku,
        unit,
        isActive,
        vendorPrices,
        createdAt,
        updatedAt,
      ];
}

/// Vendor price for product comparison
class VendorPrice extends Equatable {
  final String vendorName;
  final double price;
  final String? url;
  final DateTime updatedAt;

  const VendorPrice({
    required this.vendorName,
    required this.price,
    this.url,
    required this.updatedAt,
  });

  /// Get formatted price
  String get formattedPrice => '\$${price.toStringAsFixed(2)}';

  @override
  List<Object?> get props => [vendorName, price, url, updatedAt];
}

/// Product category enumeration
enum ProductCategory {
  plumbing,
  electrical,
  hvac,
  appliances,
  flooring,
  painting,
  roofing,
  landscaping,
  cleaning,
  security,
  general,
  other;

  String get displayName {
    switch (this) {
      case ProductCategory.plumbing:
        return 'Plumbing';
      case ProductCategory.electrical:
        return 'Electrical';
      case ProductCategory.hvac:
        return 'HVAC';
      case ProductCategory.appliances:
        return 'Appliances';
      case ProductCategory.flooring:
        return 'Flooring';
      case ProductCategory.painting:
        return 'Painting';
      case ProductCategory.roofing:
        return 'Roofing';
      case ProductCategory.landscaping:
        return 'Landscaping';
      case ProductCategory.cleaning:
        return 'Cleaning';
      case ProductCategory.security:
        return 'Security';
      case ProductCategory.general:
        return 'General';
      case ProductCategory.other:
        return 'Other';
    }
  }

  static ProductCategory fromString(String value) {
    return ProductCategory.values.firstWhere(
      (category) => category.name.toLowerCase() == value.toLowerCase(),
      orElse: () => ProductCategory.other,
    );
  }
}
