import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/properties/data/datasources/property_local_datasource.dart';
import 'package:somni_property/features/properties/data/datasources/property_remote_datasource.dart';
import 'package:somni_property/features/properties/data/repositories/property_repository_impl.dart';
import 'package:somni_property/features/properties/domain/entities/property.dart';
import 'package:somni_property/features/properties/domain/repositories/property_repository.dart';

/// Provider for PropertyLocalDataSource
final propertyLocalDataSourceProvider = Provider<PropertyLocalDataSource>((ref) {
  return PropertyLocalDataSourceImpl();
});

/// Provider for PropertyRemoteDataSource
final propertyRemoteDataSourceProvider = Provider<PropertyRemoteDataSource>((ref) {
  return PropertyRemoteDataSourceImpl(
    apiClient: ref.watch(apiClientProvider),
  );
});

/// Provider to control whether to use remote API or mock data
/// Set to true to connect to production backend
const bool _useRemoteApi = true; // Change to false for development with mock data

/// Provider for PropertyRepository
final propertyRepositoryProvider = Provider<PropertyRepository>((ref) {
  return PropertyRepositoryImpl(
    localDataSource: ref.watch(propertyLocalDataSourceProvider),
    remoteDataSource: ref.watch(propertyRemoteDataSourceProvider),
    useRemoteApi: _useRemoteApi,
  );
});

/// State for properties list
class PropertiesState {
  final List<Property> properties;
  final bool isLoading;
  final String? error;
  final PropertyType? typeFilter;
  final PropertyStatus? statusFilter;
  final String searchQuery;

  const PropertiesState({
    this.properties = const [],
    this.isLoading = false,
    this.error,
    this.typeFilter,
    this.statusFilter,
    this.searchQuery = '',
  });

  PropertiesState copyWith({
    List<Property>? properties,
    bool? isLoading,
    String? error,
    PropertyType? typeFilter,
    PropertyStatus? statusFilter,
    String? searchQuery,
    bool clearError = false,
    bool clearTypeFilter = false,
    bool clearStatusFilter = false,
  }) {
    return PropertiesState(
      properties: properties ?? this.properties,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      typeFilter: clearTypeFilter ? null : (typeFilter ?? this.typeFilter),
      statusFilter: clearStatusFilter ? null : (statusFilter ?? this.statusFilter),
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }

  /// Get filtered properties based on current filters
  List<Property> get filteredProperties {
    var result = properties;

    if (typeFilter != null) {
      result = result.where((p) => p.type == typeFilter).toList();
    }

    if (statusFilter != null) {
      result = result.where((p) => p.status == statusFilter).toList();
    }

    if (searchQuery.isNotEmpty) {
      final query = searchQuery.toLowerCase();
      result = result.where((p) {
        return p.name.toLowerCase().contains(query) ||
            p.address.toLowerCase().contains(query) ||
            p.city.toLowerCase().contains(query);
      }).toList();
    }

    return result;
  }

  /// Get property stats from current properties
  PropertyStats get stats {
    final props = properties;
    if (props.isEmpty) {
      return const PropertyStats(
        totalProperties: 0,
        totalUnits: 0,
        occupiedUnits: 0,
        availableUnits: 0,
        totalMonthlyRevenue: 0,
        averageOccupancyRate: 0,
      );
    }

    final totalUnits = props.fold<int>(0, (sum, p) => sum + p.totalUnits);
    final occupiedUnits = props.fold<int>(0, (sum, p) => sum + p.occupiedUnits);
    final totalRevenue =
        props.fold<double>(0, (sum, p) => sum + (p.monthlyRevenue ?? 0));

    return PropertyStats(
      totalProperties: props.length,
      totalUnits: totalUnits,
      occupiedUnits: occupiedUnits,
      availableUnits: totalUnits - occupiedUnits,
      totalMonthlyRevenue: totalRevenue,
      averageOccupancyRate: totalUnits > 0 ? (occupiedUnits / totalUnits) * 100 : 0,
    );
  }
}

/// Property stats class (duplicated here for convenience)
class PropertyStats {
  final int totalProperties;
  final int totalUnits;
  final int occupiedUnits;
  final int availableUnits;
  final double totalMonthlyRevenue;
  final double averageOccupancyRate;

  const PropertyStats({
    required this.totalProperties,
    required this.totalUnits,
    required this.occupiedUnits,
    required this.availableUnits,
    required this.totalMonthlyRevenue,
    required this.averageOccupancyRate,
  });
}

/// Properties state notifier
class PropertiesNotifier extends StateNotifier<PropertiesState> {
  final PropertyRepository repository;

  PropertiesNotifier({required this.repository})
      : super(const PropertiesState()) {
    loadProperties();
  }

  Future<void> loadProperties() async {
    state = state.copyWith(isLoading: true, clearError: true);

    final result = await repository.getProperties();

    result.fold(
      (failure) {
        debugPrint('PropertiesNotifier: Load failed: ${failure.message}');
        state = state.copyWith(
          isLoading: false,
          error: failure.message,
        );
      },
      (properties) {
        debugPrint('PropertiesNotifier: Loaded ${properties.length} properties');
        state = state.copyWith(
          isLoading: false,
          properties: properties,
        );
      },
    );
  }

  void setTypeFilter(PropertyType? type) {
    if (type == null) {
      state = state.copyWith(clearTypeFilter: true);
    } else {
      state = state.copyWith(typeFilter: type);
    }
  }

  void setStatusFilter(PropertyStatus? status) {
    if (status == null) {
      state = state.copyWith(clearStatusFilter: true);
    } else {
      state = state.copyWith(statusFilter: status);
    }
  }

  void setSearchQuery(String query) {
    state = state.copyWith(searchQuery: query);
  }

  void clearFilters() {
    state = state.copyWith(
      searchQuery: '',
      clearTypeFilter: true,
      clearStatusFilter: true,
    );
  }

  Future<bool> createProperty(CreatePropertyParams params) async {
    state = state.copyWith(isLoading: true, clearError: true);

    final result = await repository.createProperty(params);

    return result.fold(
      (failure) {
        state = state.copyWith(
          isLoading: false,
          error: failure.message,
        );
        return false;
      },
      (property) {
        state = state.copyWith(
          isLoading: false,
          properties: [property, ...state.properties],
        );
        return true;
      },
    );
  }

  Future<bool> updateProperty(String id, UpdatePropertyParams params) async {
    state = state.copyWith(isLoading: true, clearError: true);

    final result = await repository.updateProperty(id, params);

    return result.fold(
      (failure) {
        state = state.copyWith(
          isLoading: false,
          error: failure.message,
        );
        return false;
      },
      (updated) {
        final updatedList = state.properties.map((p) {
          return p.id == id ? updated : p;
        }).toList();
        state = state.copyWith(
          isLoading: false,
          properties: updatedList,
        );
        return true;
      },
    );
  }

  Future<bool> deleteProperty(String id) async {
    state = state.copyWith(isLoading: true, clearError: true);

    final result = await repository.deleteProperty(id);

    return result.fold(
      (failure) {
        state = state.copyWith(
          isLoading: false,
          error: failure.message,
        );
        return false;
      },
      (_) {
        final updatedList = state.properties.where((p) => p.id != id).toList();
        state = state.copyWith(
          isLoading: false,
          properties: updatedList,
        );
        return true;
      },
    );
  }
}

/// Provider for PropertiesNotifier
final propertiesProvider =
    StateNotifierProvider<PropertiesNotifier, PropertiesState>((ref) {
  return PropertiesNotifier(
    repository: ref.watch(propertyRepositoryProvider),
  );
});

/// Provider for a single property by ID
final propertyByIdProvider =
    FutureProvider.family<Property?, String>((ref, id) async {
  final repository = ref.watch(propertyRepositoryProvider);
  final result = await repository.getPropertyById(id);
  return result.fold(
    (failure) => null,
    (property) => property,
  );
});
