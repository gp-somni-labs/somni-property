import 'package:somni_property/features/quotes/domain/entities/quote.dart';
import 'package:somni_property/features/quotes/domain/entities/product.dart';

/// Quote repository interface defining data operations
abstract class QuoteRepository {
  // Quote CRUD operations
  Future<List<Quote>> getQuotes({String? status, String? clientId});
  Future<Quote> getQuoteById(String id);
  Future<Quote> createQuote(Quote quote);
  Future<Quote> updateQuote(String id, Quote quote);
  Future<void> deleteQuote(String id);

  // Quote actions
  Future<Quote> sendQuote(String id, {String? email, String? message});
  Future<Quote> approveQuote(String id, {String? token});
  Future<Quote> declineQuote(String id, {String? token, String? reason});
  Future<Quote> duplicateQuote(String id);

  // Quote calculations
  Future<Map<String, dynamic>> calculateQuote(Quote quote);

  // PDF generation
  Future<String> generateQuotePdf(String id);

  // Public portal access
  Future<Quote> getQuoteByToken(String token);
  Future<String> generatePublicToken(String id);

  // Product catalog operations
  Future<List<Product>> getProducts({String? category, String? search});
  Future<Product> getProductById(String id);
  Future<Product> createProduct(Product product);
  Future<Product> updateProduct(String id, Product product);
  Future<void> deleteProduct(String id);

  // Vendor pricing
  Future<List<Product>> syncVendorPricing();

  // Statistics
  Future<Map<String, dynamic>> getQuoteStats();
}
