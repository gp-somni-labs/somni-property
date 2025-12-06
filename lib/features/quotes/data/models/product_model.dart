import 'package:somni_property/features/quotes/domain/entities/product.dart';

/// Product model for JSON serialization
class ProductModel extends Product {
  const ProductModel({
    required super.id,
    required super.name,
    super.description,
    required super.category,
    required super.basePrice,
    super.sku,
    super.unit,
    super.isActive = true,
    super.vendorPrices = const [],
    required super.createdAt,
    required super.updatedAt,
  });

  /// Create model from JSON
  factory ProductModel.fromJson(Map<String, dynamic> json) {
    // Parse vendor prices
    List<VendorPrice> vendorPrices = [];
    if (json['vendor_prices'] != null || json['vendorPrices'] != null) {
      final prices = json['vendor_prices'] ?? json['vendorPrices'];
      vendorPrices = (prices as List)
          .map((price) => VendorPriceModel.fromJson(price))
          .toList();
    }

    return ProductModel(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      description: json['description']?.toString(),
      category: ProductCategory.fromString(
        json['category']?.toString() ?? 'other',
      ),
      basePrice: (json['base_price'] as num?)?.toDouble() ??
                 (json['basePrice'] as num?)?.toDouble() ?? 0.0,
      sku: json['sku']?.toString(),
      unit: json['unit']?.toString(),
      isActive: json['is_active'] as bool? ?? json['isActive'] as bool? ?? true,
      vendorPrices: vendorPrices,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : json['createdAt'] != null
              ? DateTime.parse(json['createdAt'])
              : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : json['updatedAt'] != null
              ? DateTime.parse(json['updatedAt'])
              : DateTime.now(),
    );
  }

  /// Convert model to JSON for API requests
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      if (description != null) 'description': description,
      'category': category.name,
      'base_price': basePrice,
      if (sku != null) 'sku': sku,
      if (unit != null) 'unit': unit,
      'is_active': isActive,
      'vendor_prices': vendorPrices
          .map((vp) => VendorPriceModel.fromEntity(vp).toJson())
          .toList(),
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  /// Create model from entity
  factory ProductModel.fromEntity(Product product) {
    return ProductModel(
      id: product.id,
      name: product.name,
      description: product.description,
      category: product.category,
      basePrice: product.basePrice,
      sku: product.sku,
      unit: product.unit,
      isActive: product.isActive,
      vendorPrices: product.vendorPrices,
      createdAt: product.createdAt,
      updatedAt: product.updatedAt,
    );
  }

  /// Convert to entity
  Product toEntity() {
    return Product(
      id: id,
      name: name,
      description: description,
      category: category,
      basePrice: basePrice,
      sku: sku,
      unit: unit,
      isActive: isActive,
      vendorPrices: vendorPrices,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }
}

/// Vendor price model for JSON serialization
class VendorPriceModel extends VendorPrice {
  const VendorPriceModel({
    required super.vendorName,
    required super.price,
    super.url,
    required super.updatedAt,
  });

  /// Create model from JSON
  factory VendorPriceModel.fromJson(Map<String, dynamic> json) {
    return VendorPriceModel(
      vendorName: json['vendor_name']?.toString() ??
                  json['vendorName']?.toString() ?? '',
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      url: json['url']?.toString(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : json['updatedAt'] != null
              ? DateTime.parse(json['updatedAt'])
              : DateTime.now(),
    );
  }

  /// Convert model to JSON for API requests
  Map<String, dynamic> toJson() {
    return {
      'vendor_name': vendorName,
      'price': price,
      if (url != null) 'url': url,
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  /// Create model from entity
  factory VendorPriceModel.fromEntity(VendorPrice vendorPrice) {
    return VendorPriceModel(
      vendorName: vendorPrice.vendorName,
      price: vendorPrice.price,
      url: vendorPrice.url,
      updatedAt: vendorPrice.updatedAt,
    );
  }

  /// Convert to entity
  VendorPrice toEntity() {
    return VendorPrice(
      vendorName: vendorName,
      price: price,
      url: url,
      updatedAt: updatedAt,
    );
  }
}
