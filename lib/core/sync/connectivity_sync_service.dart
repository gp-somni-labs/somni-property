import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:logger/logger.dart';
import 'sync_manager.dart';

/// Service that monitors connectivity and triggers automatic sync
class ConnectivitySyncService {
  final SyncManager _syncManager;
  final Connectivity _connectivity;
  final Logger _logger;

  StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;
  Timer? _periodicSyncTimer;

  bool _isOnline = false;
  bool _isSyncing = false;

  // Callbacks
  void Function()? onSyncStart;
  void Function(SyncResult result)? onSyncComplete;
  void Function(bool isOnline)? onConnectivityChange;

  ConnectivitySyncService({
    required SyncManager syncManager,
    Connectivity? connectivity,
    Logger? logger,
  })  : _syncManager = syncManager,
        _connectivity = connectivity ?? Connectivity(),
        _logger = logger ?? Logger();

  /// Initialize the connectivity sync service
  Future<void> initialize() async {
    _logger.i('Initializing ConnectivitySyncService');

    // Check initial connectivity
    final result = await _connectivity.checkConnectivity();
    _isOnline = _isConnected(result);
    _logger.i('Initial connectivity: ${_isOnline ? "online" : "offline"}');

    // Listen to connectivity changes
    _connectivitySubscription = _connectivity.onConnectivityChanged.listen(
      _onConnectivityChanged,
      onError: (error) {
        _logger.e('Connectivity stream error', error: error);
      },
    );

    // Start periodic sync timer (every 15 minutes when online)
    _startPeriodicSync();

    // Do initial sync if online
    if (_isOnline) {
      _logger.i('Device is online, triggering initial sync');
      await _triggerSync();
    }
  }

  /// Dispose and clean up resources
  Future<void> dispose() async {
    _logger.i('Disposing ConnectivitySyncService');
    await _connectivitySubscription?.cancel();
    _periodicSyncTimer?.cancel();
  }

  /// Handle connectivity changes
  void _onConnectivityChanged(List<ConnectivityResult> results) async {
    final wasOnline = _isOnline;
    _isOnline = _isConnected(results);

    _logger.i('Connectivity changed: ${_isOnline ? "online" : "offline"}');

    // Notify listeners
    onConnectivityChange?.call(_isOnline);

    // If just came online, trigger sync
    if (!wasOnline && _isOnline) {
      _logger.i('Device reconnected, triggering sync');
      await _triggerSync();
    }
  }

  /// Check if any connection result indicates connectivity
  bool _isConnected(List<ConnectivityResult> results) {
    return results.any((result) => result != ConnectivityResult.none);
  }

  /// Start periodic sync timer
  void _startPeriodicSync() {
    _periodicSyncTimer?.cancel();

    _periodicSyncTimer = Timer.periodic(
      const Duration(minutes: 15),
      (_) async {
        if (_isOnline && !_isSyncing) {
          _logger.i('Periodic sync triggered');
          await _triggerSync();
        }
      },
    );
  }

  /// Trigger a sync operation
  Future<void> _triggerSync() async {
    if (_isSyncing) {
      _logger.d('Sync already in progress, skipping');
      return;
    }

    if (!_isOnline) {
      _logger.d('Device offline, skipping sync');
      return;
    }

    try {
      _isSyncing = true;
      onSyncStart?.call();

      _logger.i('Starting automatic sync');
      final result = await _syncManager.fullSync();

      _logger.i('Automatic sync completed: $result');
      onSyncComplete?.call(result);
    } catch (e, stackTrace) {
      _logger.e('Error during automatic sync', error: e, stackTrace: stackTrace);
      onSyncComplete?.call(SyncResult(
        success: false,
        changesDownloaded: 0,
        changesUploaded: 0,
        conflictsDetected: 0,
        timestamp: DateTime.now(),
        error: e.toString(),
      ));
    } finally {
      _isSyncing = false;
    }
  }

  /// Manually trigger sync
  Future<SyncResult> manualSync() async {
    if (!_isOnline) {
      throw Exception('Cannot sync while offline');
    }

    if (_isSyncing) {
      throw Exception('Sync already in progress');
    }

    try {
      _isSyncing = true;
      onSyncStart?.call();

      _logger.i('Starting manual sync');
      final result = await _syncManager.fullSync();

      _logger.i('Manual sync completed: $result');
      onSyncComplete?.call(result);

      return result;
    } catch (e, stackTrace) {
      _logger.e('Error during manual sync', error: e, stackTrace: stackTrace);
      final result = SyncResult(
        success: false,
        changesDownloaded: 0,
        changesUploaded: 0,
        conflictsDetected: 0,
        timestamp: DateTime.now(),
        error: e.toString(),
      );
      onSyncComplete?.call(result);
      return result;
    } finally {
      _isSyncing = false;
    }
  }

  /// Get current connectivity status
  bool get isOnline => _isOnline;

  /// Check if sync is in progress
  bool get isSyncing => _isSyncing;
}
