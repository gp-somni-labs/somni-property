import 'package:workmanager/workmanager.dart';
import 'package:logger/logger.dart';

/// Callback function for background sync task
@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    final logger = Logger();

    try {
      logger.i('Background sync task started: $task');

      // Note: In production, you would initialize the sync manager here
      // and perform the sync operation. For now, we'll just log.

      // Example:
      // final database = AppDatabase();
      // final apiClient = SyncApiClient(dio);
      // final syncManager = SyncManager(database: database, apiClient: apiClient);
      // await syncManager.fullSync();

      logger.i('Background sync task completed successfully');
      return Future.value(true);
    } catch (e, stackTrace) {
      logger.e('Background sync task failed', error: e, stackTrace: stackTrace);
      return Future.value(false);
    }
  });
}

/// Service for setting up background sync
class BackgroundSyncSetup {
  static const String _syncTaskName = 'somni_property_sync';
  static const String _syncTaskTag = 'sync';

  final Logger _logger;

  BackgroundSyncSetup({Logger? logger}) : _logger = logger ?? Logger();

  /// Initialize background sync service
  Future<void> initialize() async {
    try {
      _logger.i('Initializing background sync service');

      await Workmanager().initialize(
        callbackDispatcher,
        isInDebugMode: false, // Set to true for debugging
      );

      _logger.i('Background sync service initialized');
    } catch (e, stackTrace) {
      _logger.e('Failed to initialize background sync', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Register periodic sync task (runs every 15 minutes)
  Future<void> registerPeriodicSync({
    Duration frequency = const Duration(minutes: 15),
  }) async {
    try {
      _logger.i('Registering periodic sync task with frequency: $frequency');

      await Workmanager().registerPeriodicTask(
        _syncTaskName,
        _syncTaskTag,
        frequency: frequency,
        constraints: Constraints(
          networkType: NetworkType.connected,
          requiresBatteryNotLow: true,
          requiresCharging: false,
          requiresDeviceIdle: false,
          requiresStorageNotLow: false,
        ),
        backoffPolicy: BackoffPolicy.exponential,
        backoffPolicyDelay: const Duration(minutes: 5),
        existingWorkPolicy: ExistingWorkPolicy.keep,
      );

      _logger.i('Periodic sync task registered successfully');
    } catch (e, stackTrace) {
      _logger.e('Failed to register periodic sync', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Register one-time sync task
  Future<void> registerOneTimeSync({
    Duration? initialDelay,
  }) async {
    try {
      _logger.i('Registering one-time sync task');

      await Workmanager().registerOneOffTask(
        '${_syncTaskName}_onetime',
        _syncTaskTag,
        initialDelay: initialDelay,
        constraints: Constraints(
          networkType: NetworkType.connected,
        ),
        backoffPolicy: BackoffPolicy.exponential,
        backoffPolicyDelay: const Duration(minutes: 1),
      );

      _logger.i('One-time sync task registered successfully');
    } catch (e, stackTrace) {
      _logger.e('Failed to register one-time sync', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Cancel all sync tasks
  Future<void> cancelAllSyncTasks() async {
    try {
      _logger.i('Cancelling all sync tasks');

      await Workmanager().cancelAll();

      _logger.i('All sync tasks cancelled');
    } catch (e, stackTrace) {
      _logger.e('Failed to cancel sync tasks', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Cancel periodic sync task
  Future<void> cancelPeriodicSync() async {
    try {
      _logger.i('Cancelling periodic sync task');

      await Workmanager().cancelByUniqueName(_syncTaskName);

      _logger.i('Periodic sync task cancelled');
    } catch (e, stackTrace) {
      _logger.e('Failed to cancel periodic sync', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }
}
