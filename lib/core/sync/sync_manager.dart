import 'dart:convert';
import 'dart:io';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:uuid/uuid.dart';
import 'package:logger/logger.dart';

import '../database/app_database.dart';
import 'sync_api_client.dart';
import 'sync_models.dart';
import 'entity_sync_handler.dart';

/// Main sync manager that coordinates offline sync operations
class SyncManager {
  final AppDatabase _database;
  final SyncApiClient _apiClient;
  final Logger _logger;

  // Entity sync handlers
  late final EntitySyncHandler _entityHandler;

  // Device info
  String? _deviceId;
  String? _clientId;

  SyncManager({
    required AppDatabase database,
    required SyncApiClient apiClient,
    Logger? logger,
  })  : _database = database,
        _apiClient = apiClient,
        _logger = logger ?? Logger() {
    _entityHandler = EntitySyncHandler(database: database, logger: _logger);
  }

  /// Initialize sync manager (registers device if needed)
  Future<void> initialize() async {
    try {
      _logger.i('Initializing SyncManager');

      // Get or generate device ID
      _deviceId = await _getOrCreateDeviceId();
      _logger.d('Device ID: $_deviceId');

      // Get client ID if already registered
      final clientIdMeta = await _database.getSyncMetadata('client_id');
      _clientId = clientIdMeta?.value;

      if (_clientId == null) {
        _logger.i('Device not registered, will register on first sync');
      } else {
        _logger.i('Device already registered with client ID: $_clientId');
      }
    } catch (e, stackTrace) {
      _logger.e('Error initializing SyncManager', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Register device with backend
  Future<bool> registerDevice() async {
    try {
      _logger.i('Registering device with backend');

      if (_deviceId == null) {
        _deviceId = await _getOrCreateDeviceId();
      }

      final deviceInfo = await _getDeviceInfo();
      final packageInfo = await PackageInfo.fromPlatform();

      final request = DeviceRegistrationRequest(
        deviceId: _deviceId!,
        deviceName: deviceInfo['name'],
        platform: deviceInfo['platform'],
        appVersion: packageInfo.version,
        osVersion: deviceInfo['osVersion'],
      );

      final response = await _apiClient.registerDevice(request);

      // Store client ID and registration info
      await _database.upsertSyncMetadata('client_id', response.clientId);
      await _database.upsertSyncMetadata('device_id', response.deviceId);
      await _database.upsertSyncMetadata('user_id', response.userId);

      if (response.lastSyncAt != null) {
        await _database.upsertSyncMetadata('last_sync_at', response.lastSyncAt!);
      }

      _clientId = response.clientId;

      _logger.i('Device registered successfully: ${response.message}');
      return response.isNew;
    } catch (e, stackTrace) {
      _logger.e('Error registering device', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Perform full sync (pull then push)
  Future<SyncResult> fullSync() async {
    try {
      _logger.i('Starting full sync');

      // Ensure device is registered
      if (_clientId == null) {
        await registerDevice();
      }

      // Pull changes from server
      final pullResult = await pullSync();

      // Push local changes to server
      final pushResult = await pushSync();

      _logger.i(
          'Full sync complete: downloaded ${pullResult.changesApplied}, '
          'uploaded ${pushResult.changesApplied}, '
          'conflicts: ${pushResult.conflictsDetected}');

      return SyncResult(
        success: true,
        changesDownloaded: pullResult.changesApplied,
        changesUploaded: pushResult.changesApplied,
        conflictsDetected: pushResult.conflictsDetected,
        timestamp: DateTime.now(),
      );
    } catch (e, stackTrace) {
      _logger.e('Error during full sync', error: e, stackTrace: stackTrace);
      return SyncResult(
        success: false,
        changesDownloaded: 0,
        changesUploaded: 0,
        conflictsDetected: 0,
        timestamp: DateTime.now(),
        error: e.toString(),
      );
    }
  }

  /// Pull changes from server
  Future<SyncResult> pullSync({
    List<String>? entityTypes,
    String? since,
  }) async {
    try {
      _logger.i('Starting pull sync');

      if (_deviceId == null || _clientId == null) {
        throw Exception('Device not initialized or registered');
      }

      // Get last sync timestamp if not provided
      since ??= (await _database.getSyncMetadata('last_pull_at'))?.value;

      int totalChanges = 0;
      String? cursor;
      bool hasMore = true;

      // Paginated pull
      while (hasMore) {
        final response = await _apiClient.pullSync(
          deviceId: _deviceId!,
          entityTypes: entityTypes,
          since: since,
          limit: 1000,
          cursor: cursor,
        );

        // Apply changes to local database
        for (final change in response.changes) {
          try {
            await _entityHandler.applyChange(change);
            totalChanges++;
          } catch (e) {
            _logger.w('Failed to apply change for ${change.entityType}/${change.entityId}: $e');
          }
        }

        hasMore = response.hasMore;
        cursor = response.nextCursor;

        // Update last pull timestamp
        await _database.upsertSyncMetadata('last_pull_at', response.syncTimestamp);
        await _database.upsertSyncMetadata('last_sync_at', response.syncTimestamp);
      }

      _logger.i('Pull sync complete: applied $totalChanges changes');

      return SyncResult(
        success: true,
        changesDownloaded: totalChanges,
        changesUploaded: 0,
        conflictsDetected: 0,
        timestamp: DateTime.now(),
      );
    } catch (e, stackTrace) {
      _logger.e('Error during pull sync', error: e, stackTrace: stackTrace);
      return SyncResult(
        success: false,
        changesDownloaded: 0,
        changesUploaded: 0,
        conflictsDetected: 0,
        timestamp: DateTime.now(),
        error: e.toString(),
      );
    }
  }

  /// Push local changes to server
  Future<SyncResult> pushSync() async {
    try {
      _logger.i('Starting push sync');

      if (_deviceId == null || _clientId == null) {
        throw Exception('Device not initialized or registered');
      }

      // Get pending changes from sync queue
      final pendingChanges = await _database.getPendingSyncQueue();

      if (pendingChanges.isEmpty) {
        _logger.i('No pending changes to push');
        return SyncResult(
          success: true,
          changesDownloaded: 0,
          changesUploaded: 0,
          conflictsDetected: 0,
          timestamp: DateTime.now(),
        );
      }

      _logger.i('Pushing ${pendingChanges.length} changes to server');

      // Convert to sync changes
      final syncChanges = pendingChanges.map((item) {
        return SyncChange(
          entityType: item.entityType,
          entityId: item.entityId,
          operation: item.operation,
          data: jsonDecode(item.jsonData),
          localId: item.localId,
          timestamp: item.timestamp.toIso8601String(),
          version: null, // Will be set by entity handler if UPDATE
        );
      }).toList();

      // Send to server
      final request = PushSyncRequest(
        deviceId: _deviceId!,
        changes: syncChanges,
        syncTimestamp: DateTime.now().toIso8601String(),
      );

      final response = await _apiClient.pushSync(_deviceId!, request);

      // Process results
      int applied = 0;
      int conflicts = 0;
      int errors = 0;

      for (int i = 0; i < response.results.length; i++) {
        final result = response.results[i];
        final queueItem = pendingChanges[i];

        if (result.status == 'success') {
          // Mark as synced
          await _database.markSyncQueueItemSynced(
            queueItem.id,
            serverEntityId: result.entityId,
          );

          // Update entity version in local database
          if (result.entityId != null && result.version != null) {
            await _entityHandler.updateEntityVersion(
              result.entityType,
              result.entityId!,
              result.version!,
            );
          }

          applied++;
        } else if (result.status == 'conflict') {
          // Conflict detected - keep in queue for user resolution
          conflicts++;
          _logger.w('Conflict detected for ${result.entityType}/${result.entityId}');
        } else if (result.status == 'error') {
          // Error - increment retry count
          await _database.incrementSyncQueueRetry(queueItem.id, result.error ?? 'Unknown error');
          errors++;
        }
      }

      // Update last push timestamp
      await _database.upsertSyncMetadata('last_push_at', response.syncTimestamp);
      await _database.upsertSyncMetadata('last_sync_at', response.syncTimestamp);

      _logger.i('Push sync complete: applied $applied, conflicts $conflicts, errors $errors');

      return SyncResult(
        success: true,
        changesDownloaded: 0,
        changesUploaded: applied,
        conflictsDetected: conflicts,
        timestamp: DateTime.now(),
      );
    } catch (e, stackTrace) {
      _logger.e('Error during push sync', error: e, stackTrace: stackTrace);
      return SyncResult(
        success: false,
        changesDownloaded: 0,
        changesUploaded: 0,
        conflictsDetected: 0,
        timestamp: DateTime.now(),
        error: e.toString(),
      );
    }
  }

  /// Get conflicts for current device
  Future<List<SyncConflict>> getConflicts({String? status}) async {
    try {
      if (_deviceId == null) {
        throw Exception('Device not initialized');
      }

      final response = await _apiClient.getConflicts(
        deviceId: _deviceId!,
        status: status,
      );

      return response.conflicts;
    } catch (e, stackTrace) {
      _logger.e('Error getting conflicts', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Resolve a conflict
  Future<ConflictResolutionResponse> resolveConflict({
    required String conflictId,
    required String resolutionStrategy,
    Map<String, dynamic>? resolvedData,
  }) async {
    try {
      if (_deviceId == null) {
        throw Exception('Device not initialized');
      }

      final request = ConflictResolutionRequest(
        conflictId: conflictId,
        resolutionStrategy: resolutionStrategy,
        resolvedData: resolvedData,
      );

      final response = await _apiClient.resolveConflict(_deviceId!, request);

      // Update local database with resolved version
      await _entityHandler.updateEntityVersion(
        response.entityType,
        response.entityId,
        response.newVersion,
      );

      // Remove from sync queue if present
      // (in case it was pending when conflict occurred)
      final pendingItems = await _database.getPendingSyncQueue();
      for (final item in pendingItems) {
        if (item.entityType == response.entityType && item.entityId == response.entityId) {
          await _database.markSyncQueueItemSynced(item.id);
        }
      }

      _logger.i('Conflict resolved: ${response.message}');

      return response;
    } catch (e, stackTrace) {
      _logger.e('Error resolving conflict', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Get sync status
  Future<SyncStatusResponse> getSyncStatus() async {
    if (_deviceId == null) {
      throw Exception('Device not initialized');
    }

    return await _apiClient.getSyncStatus(deviceId: _deviceId!);
  }

  /// Get or create device ID
  Future<String> _getOrCreateDeviceId() async {
    // Check if already stored
    final stored = await _database.getSyncMetadata('device_id');
    if (stored != null) {
      return stored.value;
    }

    // Generate new UUID-based device ID
    final uuid = const Uuid().v4();
    await _database.upsertSyncMetadata('device_id', uuid);
    return uuid;
  }

  /// Get device information
  Future<Map<String, String>> _getDeviceInfo() async {
    final deviceInfo = DeviceInfoPlugin();

    if (Platform.isAndroid) {
      final androidInfo = await deviceInfo.androidInfo;
      return {
        'name': '${androidInfo.manufacturer} ${androidInfo.model}',
        'platform': 'android',
        'osVersion': 'Android ${androidInfo.version.release}',
      };
    } else if (Platform.isIOS) {
      final iosInfo = await deviceInfo.iosInfo;
      return {
        'name': '${iosInfo.name} ${iosInfo.model}',
        'platform': 'ios',
        'osVersion': 'iOS ${iosInfo.systemVersion}',
      };
    } else if (Platform.isLinux) {
      final linuxInfo = await deviceInfo.linuxInfo;
      return {
        'name': linuxInfo.prettyName,
        'platform': 'linux',
        'osVersion': linuxInfo.version ?? 'Unknown',
      };
    } else if (Platform.isWindows) {
      final windowsInfo = await deviceInfo.windowsInfo;
      return {
        'name': windowsInfo.computerName,
        'platform': 'windows',
        'osVersion': 'Windows ${windowsInfo.majorVersion}.${windowsInfo.minorVersion}',
      };
    } else if (Platform.isMacOS) {
      final macOsInfo = await deviceInfo.macOsInfo;
      return {
        'name': macOsInfo.computerName,
        'platform': 'macos',
        'osVersion': 'macOS ${macOsInfo.osRelease}',
      };
    } else {
      return {
        'name': 'Unknown Device',
        'platform': 'unknown',
        'osVersion': 'Unknown',
      };
    }
  }

  /// Clean up old synced items
  Future<void> cleanupOldSyncedItems({int daysToKeep = 7}) async {
    final cutoffDate = DateTime.now().subtract(Duration(days: daysToKeep));
    await _database.cleanupSyncedItems(cutoffDate);
    _logger.i('Cleaned up synced items older than $daysToKeep days');
  }

  /// Get device ID
  String? get deviceId => _deviceId;

  /// Get client ID
  String? get clientId => _clientId;
}

/// Sync result model
class SyncResult {
  final bool success;
  final int changesDownloaded;
  final int changesUploaded;
  final int conflictsDetected;
  final DateTime timestamp;
  final String? error;

  SyncResult({
    required this.success,
    required this.changesDownloaded,
    required this.changesUploaded,
    required this.conflictsDetected,
    required this.timestamp,
    this.error,
  });

  @override
  String toString() {
    return 'SyncResult(success: $success, downloaded: $changesDownloaded, '
        'uploaded: $changesUploaded, conflicts: $conflictsDetected, error: $error)';
  }
}
