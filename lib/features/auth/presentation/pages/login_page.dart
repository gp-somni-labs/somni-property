import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/core/constants/app_constants.dart';
import 'package:somni_property/core/network/network_info.dart';
import 'package:somni_property/features/auth/domain/entities/user.dart';
import 'package:somni_property/features/auth/presentation/bloc/auth_provider.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _totpController = TextEditingController();

  bool _obscurePassword = true;
  bool _showTotpField = false;
  bool _showPasswordLogin = false; // Toggle for fallback password form

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _totpController.dispose();
    super.dispose();
  }

  /// Handle SSO login via OIDC
  Future<void> _handleSsoLogin() async {
    await ref.read(authNotifierProvider.notifier).loginWithOidc();
  }

  /// Handle password login (fallback)
  Future<void> _handlePasswordLogin() async {
    if (!_formKey.currentState!.validate()) return;

    final credentials = LoginCredentials(
      username: _usernameController.text.trim(),
      password: _passwordController.text,
      totpCode: _showTotpField ? _totpController.text.trim() : null,
    );

    await ref.read(authNotifierProvider.notifier).login(credentials);
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);
    final vpnStatus = ref.watch(vpnStatusProvider);

    // Listen for auth state changes
    ref.listen<AuthState>(authNotifierProvider, (previous, next) {
      if (next is AuthStateAuthenticated) {
        context.go('/dashboard');
      } else if (next is AuthStateRequiresTwoFactor) {
        setState(() => _showTotpField = true);
      } else if (next is AuthStateError) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next.message),
            backgroundColor: Colors.red,
          ),
        );
      }
    });

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Logo and Title
                    Icon(
                      Icons.apartment_outlined,
                      size: 80,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      AppConstants.appName,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Property Management Portal',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                            color: Colors.grey,
                          ),
                    ),
                    const SizedBox(height: 48),

                    // VPN Status Indicator
                    vpnStatus.when(
                      data: (isConnected) => _VpnStatusBadge(
                        isConnected: isConnected,
                      ),
                      loading: () => const _VpnStatusBadge(isLoading: true),
                      error: (_, __) => const _VpnStatusBadge(isConnected: false),
                    ),
                    const SizedBox(height: 32),

                    // SSO Login Button (Primary)
                    FilledButton.icon(
                      onPressed:
                          authState is AuthStateLoading ? null : _handleSsoLogin,
                      icon: authState is AuthStateLoading
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Icon(Icons.login),
                      label: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Text(
                          authState is AuthStateLoading
                              ? 'Signing in...'
                              : 'Sign in with Somni SSO',
                        ),
                      ),
                    ),

                    const SizedBox(height: 16),

                    // Toggle for password fallback
                    TextButton(
                      onPressed: () {
                        setState(() => _showPasswordLogin = !_showPasswordLogin);
                      },
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            _showPasswordLogin
                                ? Icons.expand_less
                                : Icons.expand_more,
                            size: 20,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            _showPasswordLogin
                                ? 'Hide password login'
                                : 'Use password instead',
                          ),
                        ],
                      ),
                    ),

                    // Password Login Form (Fallback - collapsible)
                    if (_showPasswordLogin) ...[
                      const SizedBox(height: 16),
                      const Divider(),
                      const SizedBox(height: 16),

                      // Username Field
                      TextFormField(
                        controller: _usernameController,
                        decoration: const InputDecoration(
                          labelText: 'Username',
                          prefixIcon: Icon(Icons.person_outline),
                        ),
                        textInputAction: TextInputAction.next,
                        autocorrect: false,
                        validator: (value) {
                          if (_showPasswordLogin &&
                              (value == null || value.trim().isEmpty)) {
                            return 'Please enter your username';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),

                      // Password Field
                      TextFormField(
                        controller: _passwordController,
                        decoration: InputDecoration(
                          labelText: 'Password',
                          prefixIcon: const Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePassword
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                            ),
                            onPressed: () {
                              setState(
                                  () => _obscurePassword = !_obscurePassword);
                            },
                          ),
                        ),
                        obscureText: _obscurePassword,
                        textInputAction: _showTotpField
                            ? TextInputAction.next
                            : TextInputAction.done,
                        onFieldSubmitted: (_) {
                          if (!_showTotpField) _handlePasswordLogin();
                        },
                        validator: (value) {
                          if (_showPasswordLogin &&
                              (value == null || value.isEmpty)) {
                            return 'Please enter your password';
                          }
                          return null;
                        },
                      ),

                      // TOTP Field (shown when 2FA required)
                      if (_showTotpField) ...[
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _totpController,
                          decoration: const InputDecoration(
                            labelText: 'Verification Code',
                            prefixIcon: Icon(Icons.security_outlined),
                            hintText: 'Enter 6-digit code',
                          ),
                          keyboardType: TextInputType.number,
                          maxLength: 6,
                          textInputAction: TextInputAction.done,
                          onFieldSubmitted: (_) => _handlePasswordLogin(),
                          validator: (value) {
                            if (_showTotpField &&
                                (value == null || value.length != 6)) {
                              return 'Please enter a valid 6-digit code';
                            }
                            return null;
                          },
                        ),
                      ],

                      const SizedBox(height: 24),

                      // Password Login Button
                      OutlinedButton(
                        onPressed: authState is AuthStateLoading
                            ? null
                            : _handlePasswordLogin,
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          child: authState is AuthStateLoading
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child:
                                      CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Text('Sign In with Password'),
                        ),
                      ),
                    ],

                    const SizedBox(height: 24),

                    // Help Text
                    Text(
                      'Connect to Tailscale VPN for secure access',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey,
                          ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _VpnStatusBadge extends StatelessWidget {
  final bool isConnected;
  final bool isLoading;

  const _VpnStatusBadge({
    this.isConnected = false,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: isLoading
            ? Colors.grey.withOpacity(0.1)
            : isConnected
                ? Colors.green.withOpacity(0.1)
                : Colors.orange.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isLoading
              ? Colors.grey
              : isConnected
                  ? Colors.green
                  : Colors.orange,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (isLoading)
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else
            Icon(
              isConnected ? Icons.vpn_lock : Icons.vpn_lock_outlined,
              size: 18,
              color: isConnected ? Colors.green : Colors.orange,
            ),
          const SizedBox(width: 8),
          Text(
            isLoading
                ? 'Checking VPN...'
                : isConnected
                    ? 'Tailscale Connected'
                    : 'VPN Not Connected',
            style: TextStyle(
              color: isLoading
                  ? Colors.grey
                  : isConnected
                      ? Colors.green
                      : Colors.orange,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
