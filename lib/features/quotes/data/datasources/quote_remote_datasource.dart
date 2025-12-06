import 'package:dio/dio.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/quotes/data/models/quote_model.dart';
import 'package:somni_property/features/quotes/data/models/product_model.dart';

/// Remote datasource for quotes API
class QuoteRemoteDataSource {
  final ApiClient apiClient;

  QuoteRemoteDataSource({required this.apiClient});

  // Quote CRUD operations
  Future<List<QuoteModel>> getQuotes({String? status, String? clientId}) async {
    final queryParams = <String, dynamic>{};
    if (status != null) queryParams['status'] = status;
    if (clientId != null) queryParams['client_id'] = clientId;

    final response = await apiClient.dio.get(
      '/quotes',
      queryParameters: queryParams,
    );
    return (response.data as List)
        .map((json) => QuoteModel.fromJson(json))
        .toList();
  }

  Future<QuoteModel> getQuoteById(String id) async {
    final response = await apiClient.dio.get('/quotes/$id');
    return QuoteModel.fromJson(response.data);
  }

  Future<QuoteModel> createQuote(QuoteModel quote) async {
    final response = await apiClient.dio.post(
      '/quotes',
      data: quote.toJson(),
    );
    return QuoteModel.fromJson(response.data);
  }

  Future<QuoteModel> updateQuote(String id, QuoteModel quote) async {
    final response = await apiClient.dio.put(
      '/quotes/$id',
      data: quote.toJson(),
    );
    return QuoteModel.fromJson(response.data);
  }

  Future<void> deleteQuote(String id) async {
    await apiClient.dio.delete('/quotes/$id');
  }

  // Quote actions
  Future<QuoteModel> sendQuote(String id,
      {String? email, String? message}) async {
    final response = await apiClient.dio.post(
      '/quotes/$id/send',
      data: {
        if (email != null) 'email': email,
        if (message != null) 'message': message,
      },
    );
    return QuoteModel.fromJson(response.data);
  }

  Future<QuoteModel> approveQuote(String id, {String? token}) async {
    final response = await apiClient.dio.post(
      '/quotes/$id/approve',
      data: {if (token != null) 'token': token},
    );
    return QuoteModel.fromJson(response.data);
  }

  Future<QuoteModel> declineQuote(String id,
      {String? token, String? reason}) async {
    final response = await apiClient.dio.post(
      '/quotes/$id/decline',
      data: {
        if (token != null) 'token': token,
        if (reason != null) 'reason': reason,
      },
    );
    return QuoteModel.fromJson(response.data);
  }

  Future<QuoteModel> duplicateQuote(String id) async {
    final response = await apiClient.dio.post('/quotes/$id/duplicate');
    return QuoteModel.fromJson(response.data);
  }

  // Quote calculations
  Future<Map<String, dynamic>> calculateQuote(QuoteModel quote) async {
    final response = await apiClient.dio.post(
      '/quotes/calculate',
      data: quote.toJson(),
    );
    return response.data as Map<String, dynamic>;
  }

  // PDF generation
  Future<String> generateQuotePdf(String id) async {
    final response = await apiClient.dio.get(
      '/quotes/$id/pdf',
      options: Options(responseType: ResponseType.bytes),
    );
    // Return base64 encoded PDF
    return response.data.toString();
  }

  // Public portal access
  Future<QuoteModel> getQuoteByToken(String token) async {
    final response = await apiClient.dio.get('/quotes/public/$token');
    return QuoteModel.fromJson(response.data);
  }

  Future<String> generatePublicToken(String id) async {
    final response = await apiClient.dio.post('/quotes/$id/generate-token');
    return response.data['token'] as String;
  }

  // Product catalog operations
  Future<List<ProductModel>> getProducts(
      {String? category, String? search}) async {
    final queryParams = <String, dynamic>{};
    if (category != null) queryParams['category'] = category;
    if (search != null) queryParams['search'] = search;

    final response = await apiClient.dio.get(
      '/products',
      queryParameters: queryParams,
    );
    return (response.data as List)
        .map((json) => ProductModel.fromJson(json))
        .toList();
  }

  Future<ProductModel> getProductById(String id) async {
    final response = await apiClient.dio.get('/products/$id');
    return ProductModel.fromJson(response.data);
  }

  Future<ProductModel> createProduct(ProductModel product) async {
    final response = await apiClient.dio.post(
      '/products',
      data: product.toJson(),
    );
    return ProductModel.fromJson(response.data);
  }

  Future<ProductModel> updateProduct(String id, ProductModel product) async {
    final response = await apiClient.dio.put(
      '/products/$id',
      data: product.toJson(),
    );
    return ProductModel.fromJson(response.data);
  }

  Future<void> deleteProduct(String id) async {
    await apiClient.dio.delete('/products/$id');
  }

  // Vendor pricing
  Future<List<ProductModel>> syncVendorPricing() async {
    final response = await apiClient.dio.post('/products/sync-vendor-pricing');
    return (response.data as List)
        .map((json) => ProductModel.fromJson(json))
        .toList();
  }

  // Statistics
  Future<Map<String, dynamic>> getQuoteStats() async {
    final response = await apiClient.dio.get('/quotes/stats');
    return response.data as Map<String, dynamic>;
  }
}
