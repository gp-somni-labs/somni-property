import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';
import 'sync_models.dart';

part 'sync_api_client.g.dart';

/// Sync API client for communicating with backend offline sync endpoints
@RestApi(baseUrl: '/api/v1/mobile-sync')
abstract class SyncApiClient {
  factory SyncApiClient(Dio dio, {String baseUrl}) = _SyncApiClient;

  /// Register device for sync
  @POST('/register')
  Future<DeviceRegistrationResponse> registerDevice(
    @Body() DeviceRegistrationRequest request,
  );

  /// Pull sync - download changes from server
  @GET('/changes')
  Future<PullSyncResponse> pullSync({
    @Header('X-Device-ID') required String deviceId,
    @Query('entity_types') List<String>? entityTypes,
    @Query('since') String? since,
    @Query('limit') int? limit,
    @Query('cursor') String? cursor,
  });

  /// Push sync - upload local changes to server
  @POST('/changes')
  Future<PushSyncResponse> pushSync(
    @Header('X-Device-ID') String deviceId,
    @Body() PushSyncRequest request,
  );

  /// Get conflicts for this device
  @GET('/conflicts')
  Future<ConflictsResponse> getConflicts({
    @Header('X-Device-ID') required String deviceId,
    @Query('status') String? status,
  });

  /// Resolve a specific conflict
  @POST('/conflicts/resolve')
  Future<ConflictResolutionResponse> resolveConflict(
    @Header('X-Device-ID') String deviceId,
    @Body() ConflictResolutionRequest request,
  );

  /// Get sync status for this device
  @GET('/status')
  Future<SyncStatusResponse> getSyncStatus({
    @Header('X-Device-ID') required String deviceId,
  });

  /// Get list of syncable entity types
  @GET('/entity-types')
  Future<EntityTypesResponse> getEntityTypes();
}
