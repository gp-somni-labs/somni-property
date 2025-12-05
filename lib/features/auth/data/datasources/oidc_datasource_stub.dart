import 'package:somni_property/features/auth/data/datasources/oidc_datasource.dart';

/// Factory function for conditional import (non-web stub)
/// This uses the flutter_appauth implementation for mobile/desktop
OidcDataSource createOidcDataSource() => OidcDataSourceImpl();
