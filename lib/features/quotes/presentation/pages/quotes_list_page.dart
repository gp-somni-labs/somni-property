import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/features/quotes/domain/entities/quote.dart';
import 'package:somni_property/features/quotes/presentation/providers/quote_provider.dart';
import 'package:somni_property/features/quotes/presentation/widgets/quote_card.dart';
import 'package:somni_property/features/quotes/presentation/pages/quote_detail_page.dart';
import 'package:somni_property/features/quotes/presentation/pages/quote_builder_page.dart';

/// Main quotes list page with tabs, search, and filters
class QuotesListPage extends ConsumerStatefulWidget {
  const QuotesListPage({super.key});

  @override
  ConsumerState<QuotesListPage> createState() => _QuotesListPageState();
}

class _QuotesListPageState extends ConsumerState<QuotesListPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _tabController.addListener(_onTabChanged);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _onTabChanged() {
    if (!_tabController.indexIsChanging) {
      final notifier = ref.read(quotesProvider.notifier);
      switch (_tabController.index) {
        case 0:
          notifier.setStatusFilter('draft');
          break;
        case 1:
          notifier.setStatusFilter('sent');
          break;
        case 2:
          notifier.setStatusFilter('approved');
          break;
        case 3:
          notifier.setStatusFilter(null);
          break;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final quotesState = ref.watch(quotesProvider);
    final statsAsyncValue = ref.watch(quoteStatsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Quotes'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Draft'),
            Tab(text: 'Sent'),
            Tab(text: 'Approved'),
            Tab(text: 'All'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: _showSearchDialog,
          ),
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
          ),
        ],
      ),
      body: Column(
        children: [
          // Stats cards
          statsAsyncValue.when(
            data: (stats) => _buildStatsCards(stats),
            loading: () => const LinearProgressIndicator(),
            error: (_, __) => const SizedBox.shrink(),
          ),

          // Quotes list
          Expanded(
            child: quotesState.isLoading
                ? const Center(child: CircularProgressIndicator())
                : quotesState.error != null
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.error_outline,
                                size: 64, color: Colors.red),
                            const SizedBox(height: 16),
                            Text(
                              'Error: ${quotesState.error}',
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: () {
                                ref.read(quotesProvider.notifier).loadQuotes();
                              },
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      )
                    : quotesState.quotes.isEmpty
                        ? _buildEmptyState()
                        : RefreshIndicator(
                            onRefresh: () =>
                                ref.read(quotesProvider.notifier).loadQuotes(),
                            child: ListView.builder(
                              itemCount: _getFilteredQuotes(quotesState.quotes).length,
                              itemBuilder: (context, index) {
                                final quote = _getFilteredQuotes(quotesState.quotes)[index];
                                return QuoteCard(
                                  quote: quote,
                                  onTap: () => _navigateToDetail(quote.id),
                                );
                              },
                            ),
                          ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _navigateToBuilder,
        icon: const Icon(Icons.add),
        label: const Text('New Quote'),
      ),
    );
  }

  Widget _buildStatsCards(stats) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: _buildStatCard(
              'Total Value',
              '\$${stats.totalValue.toStringAsFixed(0)}',
              Icons.attach_money,
              Colors.green,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildStatCard(
              'Approval Rate',
              '${stats.approvalRate.toStringAsFixed(1)}%',
              Icons.check_circle,
              Colors.blue,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildStatCard(
              'Pending',
              '${stats.pendingQuotes}',
              Icons.pending,
              Colors.orange,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 4),
            Text(
              value,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            Text(
              label,
              style: const TextStyle(fontSize: 11),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.description_outlined,
            size: 100,
            color: Colors.grey[300],
          ),
          const SizedBox(height: 16),
          Text(
            'No quotes yet',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Create your first quote to get started',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _navigateToBuilder,
            icon: const Icon(Icons.add),
            label: const Text('Create Quote'),
          ),
        ],
      ),
    );
  }

  List<Quote> _getFilteredQuotes(List<Quote> quotes) {
    if (_searchController.text.isEmpty) return quotes;

    final query = _searchController.text.toLowerCase();
    return quotes.where((quote) {
      return (quote.clientName?.toLowerCase().contains(query) ?? false) ||
          (quote.propertyAddress?.toLowerCase().contains(query) ?? false);
    }).toList();
  }

  void _showSearchDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Search Quotes'),
        content: TextField(
          controller: _searchController,
          decoration: const InputDecoration(
            hintText: 'Search by client or property...',
            prefixIcon: Icon(Icons.search),
          ),
          onChanged: (value) {
            setState(() {});
          },
        ),
        actions: [
          TextButton(
            onPressed: () {
              _searchController.clear();
              setState(() {});
              Navigator.pop(context);
            },
            child: const Text('Clear'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  void _showFilterDialog() {
    // TODO: Implement advanced filters (date range, amount range, etc.)
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Advanced filters coming soon')),
    );
  }

  void _navigateToDetail(String quoteId) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => QuoteDetailPage(quoteId: quoteId),
      ),
    );
  }

  void _navigateToBuilder() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const QuoteBuilderPage(),
      ),
    ).then((_) {
      // Refresh list after creating/editing
      ref.read(quotesProvider.notifier).loadQuotes();
    });
  }
}
