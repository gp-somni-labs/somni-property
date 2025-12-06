import 'package:dio/dio.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/quotes/data/datasources/quote_remote_datasource.dart';
import 'package:somni_property/features/quotes/data/models/quote_model.dart';
import 'package:somni_property/features/quotes/data/models/product_model.dart';
import 'package:somni_property/features/quotes/domain/entities/quote.dart';
import 'package:somni_property/features/quotes/domain/entities/product.dart';
import 'package:somni_property/features/quotes/domain/repositories/quote_repository.dart';

/// Implementation of quote repository
class QuoteRepositoryImpl implements QuoteRepository {
  final QuoteRemoteDataSource remoteDataSource;

  QuoteRepositoryImpl({required this.remoteDataSource});

  @override
  Future<List<Quote>> getQuotes({String? status, String? clientId}) async {
    try {
      final quotes = await remoteDataSource.getQuotes(
        status: status,
        clientId: clientId,
      );
      return quotes.map((model) => model.toEntity()).toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Quote> getQuoteById(String id) async {
    try {
      final quote = await remoteDataSource.getQuoteById(id);
      return quote.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Quote> createQuote(Quote quote) async {
    try {
      final quoteModel = QuoteModel.fromEntity(quote);
      final created = await remoteDataSource.createQuote(quoteModel);
      return created.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Quote> updateQuote(String id, Quote quote) async {
    try {
      final quoteModel = QuoteModel.fromEntity(quote);
      final updated = await remoteDataSource.updateQuote(id, quoteModel);
      return updated.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<void> deleteQuote(String id) async {
    try {
      await remoteDataSource.deleteQuote(id);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Quote> sendQuote(String id, {String? email, String? message}) async {
    try {
      final sent = await remoteDataSource.sendQuote(
        id,
        email: email,
        message: message,
      );
      return sent.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Quote> approveQuote(String id, {String? token}) async {
    try {
      final approved = await remoteDataSource.approveQuote(id, token: token);
      return approved.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Quote> declineQuote(String id,
      {String? token, String? reason}) async {
    try {
      final declined = await remoteDataSource.declineQuote(
        id,
        token: token,
        reason: reason,
      );
      return declined.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Quote> duplicateQuote(String id) async {
    try {
      final duplicated = await remoteDataSource.duplicateQuote(id);
      return duplicated.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Map<String, dynamic>> calculateQuote(Quote quote) async {
    try {
      final quoteModel = QuoteModel.fromEntity(quote);
      return await remoteDataSource.calculateQuote(quoteModel);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<String> generateQuotePdf(String id) async {
    try {
      return await remoteDataSource.generateQuotePdf(id);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Quote> getQuoteByToken(String token) async {
    try {
      final quote = await remoteDataSource.getQuoteByToken(token);
      return quote.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<String> generatePublicToken(String id) async {
    try {
      return await remoteDataSource.generatePublicToken(id);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<Product>> getProducts({String? category, String? search}) async {
    try {
      final products = await remoteDataSource.getProducts(
        category: category,
        search: search,
      );
      return products.map((model) => model.toEntity()).toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Product> getProductById(String id) async {
    try {
      final product = await remoteDataSource.getProductById(id);
      return product.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Product> createProduct(Product product) async {
    try {
      final productModel = ProductModel.fromEntity(product);
      final created = await remoteDataSource.createProduct(productModel);
      return created.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Product> updateProduct(String id, Product product) async {
    try {
      final productModel = ProductModel.fromEntity(product);
      final updated = await remoteDataSource.updateProduct(id, productModel);
      return updated.toEntity();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<void> deleteProduct(String id) async {
    try {
      await remoteDataSource.deleteProduct(id);
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<List<Product>> syncVendorPricing() async {
    try {
      final products = await remoteDataSource.syncVendorPricing();
      return products.map((model) => model.toEntity()).toList();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }

  @override
  Future<Map<String, dynamic>> getQuoteStats() async {
    try {
      return await remoteDataSource.getQuoteStats();
    } on DioException catch (e) {
      throw e.toAppException();
    }
  }
}
