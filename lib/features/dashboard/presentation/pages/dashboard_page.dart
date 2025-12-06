import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:somni_property/features/auth/presentation/bloc/auth_provider.dart';
import 'package:somni_property/features/dashboard/presentation/providers/dashboard_provider.dart';
import 'package:somni_property/features/dashboard/presentation/widgets/activity_feed.dart';
import 'package:somni_property/features/dashboard/presentation/widgets/alerts_banner.dart';
import 'package:somni_property/features/dashboard/presentation/widgets/dashboard_loading_shimmer.dart';
import 'package:somni_property/features/dashboard/presentation/widgets/dashboard_stat_card.dart';
import 'package:somni_property/features/dashboard/presentation/widgets/occupancy_chart.dart';
import 'package:somni_property/features/dashboard/presentation/widgets/revenue_chart.dart';

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final dashboardState = ref.watch(dashboardProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          // Refresh button
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(dashboardProvider.notifier).refresh();
            },
          ),
          // Logout button
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await ref.read(authNotifierProvider.notifier).logout();
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(dashboardProvider.notifier).refresh();
        },
        child: _buildBody(context, ref, dashboardState, user),
      ),
      floatingActionButton: _buildFAB(context),
    );
  }

  Widget _buildBody(
    BuildContext context,
    WidgetRef ref,
    dynamic dashboardState,
    dynamic user,
  ) {
    // Loading state
    if (dashboardState.isLoading && dashboardState.stats == null) {
      return const DashboardLoadingShimmer();
    }

    // Error state
    if (dashboardState.error != null && dashboardState.stats == null) {
      return DashboardErrorState(
        message: dashboardState.error!,
        onRetry: () {
          ref.read(dashboardProvider.notifier).refresh();
        },
      );
    }

    // Empty state
    if (dashboardState.isEmpty) {
      return DashboardEmptyState(
        message: 'Welcome to SomniProperty',
        subtitle: 'Get started by adding your first property',
        actionLabel: 'Add Property',
        onAction: () {
          // TODO: Navigate to add property
        },
      );
    }

    // Content
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Welcome card
          _buildWelcomeCard(context, user),
          const SizedBox(height: 24),

          // Alerts banner (if any)
          if (dashboardState.alerts.isNotEmpty) ...[
            AlertsBanner(
              alerts: dashboardState.alerts,
              onAlertTap: (alert) {
                // TODO: Navigate to alert detail
              },
              onDismiss: (alertId) {
                ref.read(dashboardProvider.notifier).dismissAlert(alertId);
              },
            ),
            const SizedBox(height: 24),
          ],

          // Stats overview
          Text(
            'Overview',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 16),
          _buildStatsGrid(context, ref, dashboardState),
          const SizedBox(height: 32),

          // Charts section
          if (MediaQuery.of(context).size.width > 800)
            _buildChartsRow(context, dashboardState)
          else
            _buildChartsColumn(context, dashboardState),
          const SizedBox(height: 32),

          // Activity feed
          if (dashboardState.activity.isNotEmpty)
            ActivityFeed(
              activities: dashboardState.activity,
              onActivityTap: (activity) {
                // TODO: Navigate to activity detail
              },
            ),
        ],
      ),
    );
  }

  Widget _buildWelcomeCard(BuildContext context, dynamic user) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              radius: 30,
              backgroundColor: Theme.of(context).colorScheme.primary,
              child: Text(
                user?.name.isNotEmpty == true ? user!.name[0].toUpperCase() : '?',
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Welcome back, ${user?.name ?? 'User'}',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  Text(
                    'Role: ${user?.role ?? 'Unknown'}',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Colors.grey,
                        ),
                  ),
                ],
              ),
            ),
            if (user != null)
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    DateFormat('MMM d, yyyy').format(DateTime.now()),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey,
                        ),
                  ),
                  Text(
                    DateFormat('h:mm a').format(DateTime.now()),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey,
                        ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsGrid(
    BuildContext context,
    WidgetRef ref,
    dynamic dashboardState,
  ) {
    final stats = dashboardState.stats;
    if (stats == null) return const SizedBox.shrink();

    final currencyFormat = NumberFormat.currency(symbol: '\$', decimalDigits: 0);

    return DashboardStatsGrid(
      stats: {
        'totalProperties': stats.totalProperties,
        'propertyTrend': stats.propertyTrend,
        'activeTenants': stats.activeTenants,
        'tenantTrend': stats.tenantTrend,
        'occupancyRate': stats.occupancyRate,
        'monthlyRevenue': stats.monthlyRevenue,
        'revenueTrend': stats.revenueTrend,
        'openWorkOrders': stats.openWorkOrders,
        'availableUnits': stats.availableUnits,
        'overduePayments': stats.overduePayments,
      },
      onCardTap: (route) {
        context.go('/$route');
      },
    );
  }

  Widget _buildChartsRow(BuildContext context, dynamic dashboardState) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          flex: 2,
          child: RevenueChart(data: dashboardState.revenue),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            children: [
              if (dashboardState.occupancy != null)
                OccupancyChart(stats: dashboardState.occupancy!),
              if (dashboardState.workOrders != null) ...[
                const SizedBox(height: 16),
                WorkOrderChart(stats: dashboardState.workOrders!),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildChartsColumn(BuildContext context, dynamic dashboardState) {
    return Column(
      children: [
        RevenueChart(data: dashboardState.revenue),
        const SizedBox(height: 16),
        if (dashboardState.occupancy != null)
          OccupancyChart(stats: dashboardState.occupancy!),
        if (dashboardState.workOrders != null) ...[
          const SizedBox(height: 16),
          WorkOrderChart(stats: dashboardState.workOrders!),
        ],
      ],
    );
  }

  Widget _buildFAB(BuildContext context) {
    return FloatingActionButton(
      onPressed: () {
        _showQuickActionsMenu(context);
      },
      child: const Icon(Icons.add),
    );
  }

  void _showQuickActionsMenu(BuildContext context) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Quick Actions',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 16),
              ListTile(
                leading: const Icon(Icons.apartment),
                title: const Text('Add Property'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Navigate to add property
                },
              ),
              ListTile(
                leading: const Icon(Icons.person_add),
                title: const Text('Add Tenant'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Navigate to add tenant
                },
              ),
              ListTile(
                leading: const Icon(Icons.description),
                title: const Text('Create Lease'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Navigate to create lease
                },
              ),
              ListTile(
                leading: const Icon(Icons.payment),
                title: const Text('Record Payment'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Navigate to record payment
                },
              ),
              ListTile(
                leading: const Icon(Icons.build),
                title: const Text('Create Work Order'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Navigate to create work order
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
