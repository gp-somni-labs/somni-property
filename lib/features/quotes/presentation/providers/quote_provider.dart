import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/quotes/data/datasources/quote_remote_datasource.dart';
import 'package:somni_property/features/quotes/data/models/quote_model.dart';
import 'package:somni_property/features/quotes/data/repositories/quote_repository_impl.dart';
import 'package:somni_property/features/quotes/domain/entities/quote.dart';
import 'package:somni_property/features/quotes/domain/entities/product.dart';
import 'package:somni_property/features/quotes/domain/repositories/quote_repository.dart';

// Repository provider
final quoteRepositoryProvider = Provider<QuoteRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final dataSource = QuoteRemoteDataSource(apiClient: apiClient);
  return QuoteRepositoryImpl(remoteDataSource: dataSource);
});

// Quotes list provider
final quotesProvider = StateNotifierProvider<QuotesNotifier, QuotesState>((ref) {
  final repository = ref.watch(quoteRepositoryProvider);
  return QuotesNotifier(repository);
});

// Quote detail provider
final quoteDetailProvider =
    StateNotifierProvider.family<QuoteDetailNotifier, QuoteDetailState, String>(
  (ref, quoteId) {
    final repository = ref.watch(quoteRepositoryProvider);
    return QuoteDetailNotifier(repository, quoteId);
  },
);

// Products catalog provider
final productsProvider =
    StateNotifierProvider<ProductsNotifier, ProductsState>((ref) {
  final repository = ref.watch(quoteRepositoryProvider);
  return ProductsNotifier(repository);
});

// Quote stats provider
final quoteStatsProvider = FutureProvider<QuoteStatsModel>((ref) async {
  final repository = ref.watch(quoteRepositoryProvider);
  final stats = await repository.getQuoteStats();
  return QuoteStatsModel.fromJson(stats);
});

// ============================================================================
// QUOTES STATE MANAGEMENT
// ============================================================================

class QuotesState {
  final List<Quote> quotes;
  final bool isLoading;
  final String? error;
  final String? statusFilter;
  final String? searchQuery;

  const QuotesState({
    this.quotes = const [],
    this.isLoading = false,
    this.error,
    this.statusFilter,
    this.searchQuery,
  });

  QuotesState copyWith({
    List<Quote>? quotes,
    bool? isLoading,
    String? error,
    String? statusFilter,
    String? searchQuery,
  }) {
    return QuotesState(
      quotes: quotes ?? this.quotes,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      statusFilter: statusFilter ?? this.statusFilter,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }
}

class QuotesNotifier extends StateNotifier<QuotesState> {
  final QuoteRepository _repository;

  QuotesNotifier(this._repository) : super(const QuotesState()) {
    loadQuotes();
  }

  Future<void> loadQuotes() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final quotes = await _repository.getQuotes(
        status: state.statusFilter,
      );
      state = state.copyWith(quotes: quotes, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        error: e.toString(),
        isLoading: false,
      );
      debugPrint('Error loading quotes: $e');
    }
  }

  void setStatusFilter(String? status) {
    state = state.copyWith(statusFilter: status);
    loadQuotes();
  }

  void setSearchQuery(String? query) {
    state = state.copyWith(searchQuery: query);
  }

  Future<void> deleteQuote(String id) async {
    try {
      await _repository.deleteQuote(id);
      await loadQuotes();
    } catch (e) {
      debugPrint('Error deleting quote: $e');
      rethrow;
    }
  }
}

// ============================================================================
// QUOTE DETAIL STATE MANAGEMENT
// ============================================================================

class QuoteDetailState {
  final Quote? quote;
  final bool isLoading;
  final String? error;
  final bool isProcessing;

  const QuoteDetailState({
    this.quote,
    this.isLoading = false,
    this.error,
    this.isProcessing = false,
  });

  QuoteDetailState copyWith({
    Quote? quote,
    bool? isLoading,
    String? error,
    bool? isProcessing,
  }) {
    return QuoteDetailState(
      quote: quote ?? this.quote,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      isProcessing: isProcessing ?? this.isProcessing,
    );
  }
}

class QuoteDetailNotifier extends StateNotifier<QuoteDetailState> {
  final QuoteRepository _repository;
  final String _quoteId;

  QuoteDetailNotifier(this._repository, this._quoteId)
      : super(const QuoteDetailState()) {
    loadQuote();
  }

  Future<void> loadQuote() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final quote = await _repository.getQuoteById(_quoteId);
      state = state.copyWith(quote: quote, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        error: e.toString(),
        isLoading: false,
      );
      debugPrint('Error loading quote: $e');
    }
  }

  Future<void> sendQuote({String? email, String? message}) async {
    state = state.copyWith(isProcessing: true);
    try {
      final updated = await _repository.sendQuote(
        _quoteId,
        email: email,
        message: message,
      );
      state = state.copyWith(quote: updated, isProcessing: false);
    } catch (e) {
      state = state.copyWith(isProcessing: false);
      debugPrint('Error sending quote: $e');
      rethrow;
    }
  }

  Future<void> approveQuote() async {
    state = state.copyWith(isProcessing: true);
    try {
      final updated = await _repository.approveQuote(_quoteId);
      state = state.copyWith(quote: updated, isProcessing: false);
    } catch (e) {
      state = state.copyWith(isProcessing: false);
      debugPrint('Error approving quote: $e');
      rethrow;
    }
  }

  Future<void> declineQuote({String? reason}) async {
    state = state.copyWith(isProcessing: true);
    try {
      final updated = await _repository.declineQuote(
        _quoteId,
        reason: reason,
      );
      state = state.copyWith(quote: updated, isProcessing: false);
    } catch (e) {
      state = state.copyWith(isProcessing: false);
      debugPrint('Error declining quote: $e');
      rethrow;
    }
  }

  Future<String> generatePdf() async {
    try {
      return await _repository.generateQuotePdf(_quoteId);
    } catch (e) {
      debugPrint('Error generating PDF: $e');
      rethrow;
    }
  }

  Future<Quote> duplicateQuote() async {
    try {
      return await _repository.duplicateQuote(_quoteId);
    } catch (e) {
      debugPrint('Error duplicating quote: $e');
      rethrow;
    }
  }
}

// ============================================================================
// PRODUCTS STATE MANAGEMENT
// ============================================================================

class ProductsState {
  final List<Product> products;
  final bool isLoading;
  final String? error;
  final String? categoryFilter;
  final String? searchQuery;

  const ProductsState({
    this.products = const [],
    this.isLoading = false,
    this.error,
    this.categoryFilter,
    this.searchQuery,
  });

  ProductsState copyWith({
    List<Product>? products,
    bool? isLoading,
    String? error,
    String? categoryFilter,
    String? searchQuery,
  }) {
    return ProductsState(
      products: products ?? this.products,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      categoryFilter: categoryFilter ?? this.categoryFilter,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }
}

class ProductsNotifier extends StateNotifier<ProductsState> {
  final QuoteRepository _repository;

  ProductsNotifier(this._repository) : super(const ProductsState()) {
    loadProducts();
  }

  Future<void> loadProducts() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final products = await _repository.getProducts(
        category: state.categoryFilter,
        search: state.searchQuery,
      );
      state = state.copyWith(products: products, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        error: e.toString(),
        isLoading: false,
      );
      debugPrint('Error loading products: $e');
    }
  }

  void setCategoryFilter(String? category) {
    state = state.copyWith(categoryFilter: category);
    loadProducts();
  }

  void setSearchQuery(String? query) {
    state = state.copyWith(searchQuery: query);
    loadProducts();
  }
}
