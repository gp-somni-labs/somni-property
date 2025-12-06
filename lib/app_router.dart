import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/auth/presentation/bloc/auth_provider.dart';
import 'package:somni_property/features/auth/presentation/pages/login_page.dart';
import 'package:somni_property/features/dashboard/presentation/pages/dashboard_page.dart';
import 'package:somni_property/features/properties/presentation/pages/properties_list_page.dart';
import 'package:somni_property/features/properties/presentation/pages/property_detail_page.dart';
import 'package:somni_property/features/properties/presentation/pages/property_form_page.dart';
import 'package:somni_property/features/tenants/presentation/pages/tenants_list_page.dart';
import 'package:somni_property/features/tenants/presentation/pages/tenant_detail_page.dart';
import 'package:somni_property/features/tenants/presentation/pages/tenant_form_page.dart';
import 'package:somni_property/features/leases/presentation/pages/leases_list_page.dart';
import 'package:somni_property/features/leases/presentation/pages/lease_detail_page.dart';
import 'package:somni_property/features/leases/presentation/pages/lease_form_page.dart';
import 'package:somni_property/features/payments/presentation/pages/payments_list_page.dart';
import 'package:somni_property/features/payments/presentation/pages/payment_detail_page.dart';
import 'package:somni_property/features/payments/presentation/pages/payment_form_page.dart';
import 'package:somni_property/features/work_orders/presentation/pages/work_orders_list_page.dart';
import 'package:somni_property/features/work_orders/presentation/pages/work_order_detail_page.dart';
import 'package:somni_property/features/work_orders/presentation/pages/work_order_form_page.dart';

/// Router provider for web-compatible navigation
final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authNotifierProvider);

  return GoRouter(
    initialLocation: '/',
    debugLogDiagnostics: true,
    redirect: (context, state) {
      final isAuthenticated = authState is AuthStateAuthenticated;
      final isLoggingIn = state.matchedLocation == '/login';

      // If not authenticated, redirect to login
      if (!isAuthenticated && !isLoggingIn) {
        return '/login';
      }

      // If authenticated and on login page, redirect to home
      if (isAuthenticated && isLoggingIn) {
        return '/dashboard';
      }

      return null;
    },
    routes: [
      // Login
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const LoginPage(),
      ),

      // Main app shell
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          // Dashboard (Landing Page)
          GoRoute(
            path: '/',
            name: 'home',
            redirect: (context, state) => '/dashboard',
          ),
          GoRoute(
            path: '/dashboard',
            name: 'dashboard',
            builder: (context, state) => const DashboardPage(),
          ),

          // Properties List
          GoRoute(
            path: '/properties',
            name: 'properties',
            builder: (context, state) => const PropertiesListPage(),
            routes: [
              // New Property
              GoRoute(
                path: 'new',
                name: 'propertyNew',
                builder: (context, state) => const PropertyFormPage(),
              ),
              // Property Detail
              GoRoute(
                path: ':id',
                name: 'propertyDetail',
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return PropertyDetailPage(propertyId: id);
                },
                routes: [
                  // Edit Property
                  GoRoute(
                    path: 'edit',
                    name: 'propertyEdit',
                    builder: (context, state) {
                      final id = state.pathParameters['id']!;
                      return PropertyFormPage(propertyId: id);
                    },
                  ),
                ],
              ),
            ],
          ),

          // Tenants
          GoRoute(
            path: '/tenants',
            name: 'tenants',
            builder: (context, state) => const TenantsListPage(),
            routes: [
              // New Tenant
              GoRoute(
                path: 'new',
                name: 'tenantNew',
                builder: (context, state) => const TenantFormPage(),
              ),
              // Tenant Detail
              GoRoute(
                path: ':id',
                name: 'tenantDetail',
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return TenantDetailPage(tenantId: id);
                },
                routes: [
                  // Edit Tenant
                  GoRoute(
                    path: 'edit',
                    name: 'tenantEdit',
                    builder: (context, state) {
                      final id = state.pathParameters['id']!;
                      return TenantFormPage(tenantId: id);
                    },
                  ),
                ],
              ),
            ],
          ),

          // Leases
          GoRoute(
            path: '/leases',
            name: 'leases',
            builder: (context, state) => const LeasesListPage(),
            routes: [
              // New Lease
              GoRoute(
                path: 'new',
                name: 'leaseNew',
                builder: (context, state) => const LeaseFormPage(),
              ),
              // Lease Detail
              GoRoute(
                path: ':id',
                name: 'leaseDetail',
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return LeaseDetailPage(leaseId: id);
                },
                routes: [
                  // Edit Lease
                  GoRoute(
                    path: 'edit',
                    name: 'leaseEdit',
                    builder: (context, state) {
                      final id = state.pathParameters['id']!;
                      return LeaseFormPage(leaseId: id);
                    },
                  ),
                ],
              ),
            ],
          ),

          // Payments
          GoRoute(
            path: '/payments',
            name: 'payments',
            builder: (context, state) => const PaymentsListPage(),
            routes: [
              // New Payment
              GoRoute(
                path: 'new',
                name: 'paymentNew',
                builder: (context, state) => const PaymentFormPage(),
              ),
              // Payment Detail
              GoRoute(
                path: ':id',
                name: 'paymentDetail',
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return PaymentDetailPage(paymentId: id);
                },
                routes: [
                  // Edit Payment
                  GoRoute(
                    path: 'edit',
                    name: 'paymentEdit',
                    builder: (context, state) {
                      final id = state.pathParameters['id']!;
                      return PaymentFormPage(paymentId: id);
                    },
                  ),
                ],
              ),
            ],
          ),

          // Maintenance (Work Orders)
          GoRoute(
            path: '/maintenance',
            name: 'maintenance',
            builder: (context, state) => const WorkOrdersListPage(),
            routes: [
              // New Work Order
              GoRoute(
                path: 'new',
                name: 'maintenanceNew',
                builder: (context, state) => const WorkOrderFormPage(),
              ),
              // Work Order Detail
              GoRoute(
                path: ':id',
                name: 'maintenanceDetail',
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return WorkOrderDetailPage(workOrderId: id);
                },
                routes: [
                  // Edit Work Order
                  GoRoute(
                    path: 'edit',
                    name: 'maintenanceEdit',
                    builder: (context, state) {
                      final id = state.pathParameters['id']!;
                      return WorkOrderFormPage(workOrderId: id);
                    },
                  ),
                ],
              ),
            ],
          ),

          // Settings
          GoRoute(
            path: '/settings',
            name: 'settings',
            builder: (context, state) => const SettingsPlaceholderPage(),
          ),
        ],
      ),
    ],
    errorBuilder: (context, state) => ErrorPage(error: state.error),
  );
});

/// App shell with navigation
class AppShell extends ConsumerWidget {
  final Widget child;

  const AppShell({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isWide = MediaQuery.of(context).size.width > 800;

    if (isWide) {
      // Desktop layout with sidebar
      return Scaffold(
        body: Row(
          children: [
            NavigationRail(
              selectedIndex: _getSelectedIndex(context),
              onDestinationSelected: (index) => _onDestinationSelected(context, index),
              labelType: NavigationRailLabelType.all,
              leading: Padding(
                padding: const EdgeInsets.all(16),
                child: Icon(
                  Icons.apartment,
                  size: 40,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),
              trailing: Expanded(
                child: Align(
                  alignment: Alignment.bottomCenter,
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: IconButton(
                      icon: const Icon(Icons.logout),
                      onPressed: () {
                        ref.read(authNotifierProvider.notifier).logout();
                      },
                    ),
                  ),
                ),
              ),
              destinations: const [
                NavigationRailDestination(
                  icon: Icon(Icons.dashboard_outlined),
                  selectedIcon: Icon(Icons.dashboard),
                  label: Text('Dashboard'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.apartment_outlined),
                  selectedIcon: Icon(Icons.apartment),
                  label: Text('Properties'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.people_outlined),
                  selectedIcon: Icon(Icons.people),
                  label: Text('Tenants'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.description_outlined),
                  selectedIcon: Icon(Icons.description),
                  label: Text('Leases'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.build_outlined),
                  selectedIcon: Icon(Icons.build),
                  label: Text('Maintenance'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.settings_outlined),
                  selectedIcon: Icon(Icons.settings),
                  label: Text('Settings'),
                ),
              ],
            ),
            const VerticalDivider(thickness: 1, width: 1),
            Expanded(child: child),
          ],
        ),
      );
    }

    // Mobile layout with bottom navigation
    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _getSelectedIndex(context),
        onDestinationSelected: (index) => _onDestinationSelected(context, index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.apartment_outlined),
            selectedIcon: Icon(Icons.apartment),
            label: 'Properties',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outlined),
            selectedIcon: Icon(Icons.people),
            label: 'Tenants',
          ),
          NavigationDestination(
            icon: Icon(Icons.build_outlined),
            selectedIcon: Icon(Icons.build),
            label: 'Maintenance',
          ),
        ],
      ),
    );
  }

  int _getSelectedIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    if (location.startsWith('/properties')) return 1;
    if (location.startsWith('/tenants')) return 2;
    if (location.startsWith('/leases')) return 3;
    if (location.startsWith('/maintenance')) return 4;
    if (location.startsWith('/settings')) return 5;
    return 0; // Dashboard
  }

  void _onDestinationSelected(BuildContext context, int index) {
    switch (index) {
      case 0:
        context.go('/dashboard');
        break;
      case 1:
        context.go('/properties');
        break;
      case 2:
        context.go('/tenants');
        break;
      case 3:
        context.go('/leases');
        break;
      case 4:
        context.go('/maintenance');
        break;
      case 5:
        context.go('/settings');
        break;
    }
  }
}

// Placeholder pages - to be implemented

class SettingsPlaceholderPage extends StatelessWidget {
  const SettingsPlaceholderPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: const Center(child: Text('Settings coming soon')),
    );
  }
}

/// Error page
class ErrorPage extends StatelessWidget {
  final Exception? error;

  const ErrorPage({super.key, this.error});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Error')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              'Page not found',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(error?.toString() ?? 'Unknown error'),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () => context.go('/dashboard'),
              child: const Text('Go Home'),
            ),
          ],
        ),
      ),
    );
  }
}
