import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:somni_property/core/sync/sync_manager.dart';
import 'package:somni_property/core/sync/sync_api_client.dart';
import 'package:somni_property/core/sync/sync_models.dart';
import 'package:somni_property/core/database/app_database.dart';

// Generate mocks
@GenerateMocks([SyncApiClient, AppDatabase])
import 'sync_manager_test.mocks.dart';

void main() {
  late MockSyncApiClient mockApiClient;
  late MockAppDatabase mockDatabase;
  late SyncManager syncManager;

  setUp(() {
    mockApiClient = MockSyncApiClient();
    mockDatabase = MockAppDatabase();
    syncManager = SyncManager(
      database: mockDatabase,
      apiClient: mockApiClient,
    );
  });

  group('SyncManager', () {
    group('registerDevice', () {
      test('should register device and store client ID', () async {
        // Arrange
        final response = DeviceRegistrationResponse(
          clientId: 'test-client-id',
          deviceId: 'test-device-id',
          userId: 'test-user-id',
          isNew: true,
          message: 'Device registered',
        );

        when(mockApiClient.registerDevice(any))
            .thenAnswer((_) async => response);

        when(mockDatabase.upsertSyncMetadata(any, any))
            .thenAnswer((_) async => {});

        when(mockDatabase.getSyncMetadata('device_id'))
            .thenAnswer((_) async => SyncMetadataTableData(
                  key: 'device_id',
                  value: 'test-device-id',
                  updatedAt: DateTime.now(),
                ));

        // Act
        await syncManager.initialize();
        final isNew = await syncManager.registerDevice();

        // Assert
        expect(isNew, true);
        verify(mockApiClient.registerDevice(any)).called(1);
        verify(mockDatabase.upsertSyncMetadata('client_id', 'test-client-id'))
            .called(1);
      });
    });

    group('pullSync', () {
      test('should fetch changes and apply to local database', () async {
        // Arrange
        final changes = [
          SyncChange(
            entityType: 'work_orders',
            entityId: 'test-work-order-id',
            operation: 'UPDATE',
            data: {
              'id': 'test-work-order-id',
              'status': 'completed',
              'version': 5,
            },
            version: 5,
          ),
        ];

        final response = PullSyncResponse(
          changes: changes,
          syncTimestamp: DateTime.now().toIso8601String(),
          hasMore: false,
          totalChanges: 1,
        );

        when(mockApiClient.pullSync(
          deviceId: anyNamed('deviceId'),
          entityTypes: anyNamed('entityTypes'),
          since: anyNamed('since'),
          limit: anyNamed('limit'),
          cursor: anyNamed('cursor'),
        )).thenAnswer((_) async => response);

        when(mockDatabase.upsertSyncMetadata(any, any))
            .thenAnswer((_) async => {});

        when(mockDatabase.getSyncMetadata(any))
            .thenAnswer((_) async => null);

        // TODO: Mock entity handler to avoid database operations

        // Act
        final result = await syncManager.pullSync();

        // Assert
        expect(result.success, true);
        expect(result.changesDownloaded, 1);
        verify(mockApiClient.pullSync(
          deviceId: anyNamed('deviceId'),
          entityTypes: anyNamed('entityTypes'),
          since: anyNamed('since'),
          limit: anyNamed('limit'),
          cursor: anyNamed('cursor'),
        )).called(1);
      });

      test('should handle pagination correctly', () async {
        // Arrange
        final firstResponse = PullSyncResponse(
          changes: [
            SyncChange(
              entityType: 'work_orders',
              entityId: 'id-1',
              operation: 'UPDATE',
              data: {'id': 'id-1'},
            ),
          ],
          syncTimestamp: DateTime.now().toIso8601String(),
          hasMore: true,
          nextCursor: 'cursor-1',
          totalChanges: 2,
        );

        final secondResponse = PullSyncResponse(
          changes: [
            SyncChange(
              entityType: 'work_orders',
              entityId: 'id-2',
              operation: 'UPDATE',
              data: {'id': 'id-2'},
            ),
          ],
          syncTimestamp: DateTime.now().toIso8601String(),
          hasMore: false,
          totalChanges: 2,
        );

        when(mockApiClient.pullSync(
          deviceId: anyNamed('deviceId'),
          cursor: null,
        )).thenAnswer((_) async => firstResponse);

        when(mockApiClient.pullSync(
          deviceId: anyNamed('deviceId'),
          cursor: 'cursor-1',
        )).thenAnswer((_) async => secondResponse);

        when(mockDatabase.upsertSyncMetadata(any, any))
            .thenAnswer((_) async => {});

        when(mockDatabase.getSyncMetadata(any))
            .thenAnswer((_) async => null);

        // Act
        final result = await syncManager.pullSync();

        // Assert
        expect(result.success, true);
        expect(result.changesDownloaded, 2);
        verify(mockApiClient.pullSync(
          deviceId: anyNamed('deviceId'),
          cursor: argThat(isNull, named: 'cursor'),
        )).called(1);
        verify(mockApiClient.pullSync(
          deviceId: anyNamed('deviceId'),
          cursor: 'cursor-1',
        )).called(1);
      });
    });

    group('pushSync', () {
      test('should upload pending changes and mark as synced', () async {
        // Arrange
        final pendingChanges = [
          SyncQueueTableData(
            id: 1,
            entityType: 'work_orders',
            entityId: 'test-id',
            operation: 'UPDATE',
            jsonData: '{"id":"test-id","status":"completed"}',
            localId: null,
            timestamp: DateTime.now(),
            isSynced: false,
            syncedAt: null,
            retryCount: 0,
            lastError: null,
            serverEntityId: null,
          ),
        ];

        final response = PushSyncResponse(
          results: [
            PushSyncResult(
              entityId: 'test-id',
              entityType: 'work_orders',
              operation: 'UPDATE',
              status: 'success',
              version: 6,
            ),
          ],
          syncTimestamp: DateTime.now().toIso8601String(),
          totalApplied: 1,
          totalConflicts: 0,
          totalErrors: 0,
          message: 'Applied 1, 0 conflicts, 0 errors',
        );

        when(mockDatabase.getPendingSyncQueue())
            .thenAnswer((_) async => pendingChanges);

        when(mockApiClient.pushSync(any, any))
            .thenAnswer((_) async => response);

        when(mockDatabase.markSyncQueueItemSynced(any, serverEntityId: anyNamed('serverEntityId')))
            .thenAnswer((_) async => {});

        when(mockDatabase.upsertSyncMetadata(any, any))
            .thenAnswer((_) async => {});

        // Act
        final result = await syncManager.pushSync();

        // Assert
        expect(result.success, true);
        expect(result.changesUploaded, 1);
        expect(result.conflictsDetected, 0);
        verify(mockDatabase.markSyncQueueItemSynced(1, serverEntityId: anyNamed('serverEntityId')))
            .called(1);
      });

      test('should detect conflicts and keep in queue', () async {
        // Arrange
        final pendingChanges = [
          SyncQueueTableData(
            id: 1,
            entityType: 'work_orders',
            entityId: 'test-id',
            operation: 'UPDATE',
            jsonData: '{"id":"test-id","status":"completed"}',
            localId: null,
            timestamp: DateTime.now(),
            isSynced: false,
            syncedAt: null,
            retryCount: 0,
            lastError: null,
            serverEntityId: null,
          ),
        ];

        final response = PushSyncResponse(
          results: [
            PushSyncResult(
              entityId: 'test-id',
              entityType: 'work_orders',
              operation: 'UPDATE',
              status: 'conflict',
              conflictId: 'conflict-123',
            ),
          ],
          syncTimestamp: DateTime.now().toIso8601String(),
          totalApplied: 0,
          totalConflicts: 1,
          totalErrors: 0,
          message: 'Applied 0, 1 conflicts, 0 errors',
        );

        when(mockDatabase.getPendingSyncQueue())
            .thenAnswer((_) async => pendingChanges);

        when(mockApiClient.pushSync(any, any))
            .thenAnswer((_) async => response);

        when(mockDatabase.upsertSyncMetadata(any, any))
            .thenAnswer((_) async => {});

        // Act
        final result = await syncManager.pushSync();

        // Assert
        expect(result.success, true);
        expect(result.changesUploaded, 0);
        expect(result.conflictsDetected, 1);
        verifyNever(mockDatabase.markSyncQueueItemSynced(any, serverEntityId: anyNamed('serverEntityId')));
      });

      test('should increment retry count on error', () async {
        // Arrange
        final pendingChanges = [
          SyncQueueTableData(
            id: 1,
            entityType: 'work_orders',
            entityId: 'test-id',
            operation: 'UPDATE',
            jsonData: '{"id":"test-id","status":"completed"}',
            localId: null,
            timestamp: DateTime.now(),
            isSynced: false,
            syncedAt: null,
            retryCount: 0,
            lastError: null,
            serverEntityId: null,
          ),
        ];

        final response = PushSyncResponse(
          results: [
            PushSyncResult(
              entityId: 'test-id',
              entityType: 'work_orders',
              operation: 'UPDATE',
              status: 'error',
              error: 'Database error',
            ),
          ],
          syncTimestamp: DateTime.now().toIso8601String(),
          totalApplied: 0,
          totalConflicts: 0,
          totalErrors: 1,
          message: 'Applied 0, 0 conflicts, 1 errors',
        );

        when(mockDatabase.getPendingSyncQueue())
            .thenAnswer((_) async => pendingChanges);

        when(mockApiClient.pushSync(any, any))
            .thenAnswer((_) async => response);

        when(mockDatabase.incrementSyncQueueRetry(any, any))
            .thenAnswer((_) async => {});

        when(mockDatabase.upsertSyncMetadata(any, any))
            .thenAnswer((_) async => {});

        // Act
        final result = await syncManager.pushSync();

        // Assert
        expect(result.success, true);
        expect(result.changesUploaded, 0);
        verify(mockDatabase.incrementSyncQueueRetry(1, 'Database error'))
            .called(1);
      });
    });

    group('fullSync', () {
      test('should perform both pull and push sync', () async {
        // Arrange
        // Mock pull sync
        when(mockApiClient.pullSync(
          deviceId: anyNamed('deviceId'),
        )).thenAnswer((_) async => PullSyncResponse(
              changes: [],
              syncTimestamp: DateTime.now().toIso8601String(),
              hasMore: false,
              totalChanges: 0,
            ));

        // Mock push sync
        when(mockDatabase.getPendingSyncQueue())
            .thenAnswer((_) async => []);

        when(mockDatabase.upsertSyncMetadata(any, any))
            .thenAnswer((_) async => {});

        when(mockDatabase.getSyncMetadata(any))
            .thenAnswer((_) async => null);

        // Act
        final result = await syncManager.fullSync();

        // Assert
        expect(result.success, true);
        verify(mockApiClient.pullSync(deviceId: anyNamed('deviceId')))
            .called(1);
        verify(mockDatabase.getPendingSyncQueue()).called(1);
      });
    });

    group('resolveConflict', () {
      test('should resolve conflict with server_wins strategy', () async {
        // Arrange
        final response = ConflictResolutionResponse(
          conflictId: 'conflict-123',
          status: 'resolved',
          entityId: 'test-id',
          entityType: 'work_orders',
          newVersion: 7,
          message: 'Conflict resolved using server_wins',
        );

        when(mockApiClient.resolveConflict(any, any))
            .thenAnswer((_) async => response);

        when(mockDatabase.getPendingSyncQueue())
            .thenAnswer((_) async => []);

        // Act
        final result = await syncManager.resolveConflict(
          conflictId: 'conflict-123',
          resolutionStrategy: 'server_wins',
        );

        // Assert
        expect(result.status, 'resolved');
        expect(result.newVersion, 7);
        verify(mockApiClient.resolveConflict(any, any)).called(1);
      });
    });
  });
}
