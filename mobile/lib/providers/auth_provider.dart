import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/auth_response.dart';
import '../services/auth_service.dart';

/// Authentication state for the app
class AuthState {
  final AuthUser? user;
  final List<Organization>? organizations;
  final Organization? selectedOrganization;
  final bool isLoading;
  final bool isAuthenticated;
  final String? error;

  const AuthState({
    this.user,
    this.organizations,
    this.selectedOrganization,
    this.isLoading = false,
    this.isAuthenticated = false,
    this.error,
  });

  /// Initial state
  const AuthState.initial()
    : user = null,
      organizations = null,
      selectedOrganization = null,
      isLoading = false,
      isAuthenticated = false,
      error = null;

  /// Check if user needs to select an organization
  bool get needsOrgSelection =>
      isAuthenticated &&
      organizations != null &&
      organizations!.isNotEmpty &&
      selectedOrganization == null;

  /// Create a copy with updated fields
  /// Use [clearSelectedOrganization] to explicitly set selectedOrganization to null
  AuthState copyWith({
    AuthUser? user,
    List<Organization>? organizations,
    Organization? selectedOrganization,
    bool? isLoading,
    bool? isAuthenticated,
    String? error,
    bool clearError = false,
    bool clearSelectedOrganization = false,
  }) {
    return AuthState(
      user: user ?? this.user,
      organizations: organizations ?? this.organizations,
      selectedOrganization: clearSelectedOrganization
          ? null
          : (selectedOrganization ?? this.selectedOrganization),
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      error: clearError ? null : (error ?? this.error),
    );
  }

  @override
  String toString() =>
      'AuthState(isAuthenticated: $isAuthenticated, user: ${user?.email}, isLoading: $isLoading)';
}

/// Notifier for authentication state changes
class AuthNotifier extends Notifier<AuthState> {
  final AuthService _authService = AuthService();

  @override
  AuthState build() => const AuthState.initial();

  /// Check if user is already authenticated (on app launch)
  Future<void> checkAuthStatus() async {
    debugPrint('AuthNotifier: Checking auth status...');

    state = state.copyWith(isLoading: true, clearError: true);

    // AuthService.initialize() should have been called before this
    final isLoggedIn = _authService.isLoggedIn;

    state = state.copyWith(
      isLoading: false,
      isAuthenticated: isLoggedIn,
      user: _authService.currentUser,
      organizations: _authService.organizations,
      selectedOrganization: _authService.selectedOrganization,
    );

    debugPrint(
      'AuthNotifier: Auth status checked, isAuthenticated: ${state.isAuthenticated}',
    );
  }

  /// Sign in with Google
  Future<bool> signInWithGoogle() async {
    debugPrint('AuthNotifier: Starting Google sign-in...');

    state = state.copyWith(isLoading: true, clearError: true);

    try {
      final success = await _authService.signInWithGoogle();
      if (!ref.mounted) return success;

      if (success) {
        // Fresh Google sign-in clears selected org - user must select again
        state = state.copyWith(
          isLoading: false,
          isAuthenticated: true,
          user: _authService.currentUser,
          organizations: _authService.organizations,
          clearSelectedOrganization: true,
        );

        debugPrint('AuthNotifier: Google sign-in successful');
        return true;
      } else {
        state = state.copyWith(
          isLoading: false,
          error: 'Sign-in was cancelled or failed. Please try again.',
        );

        debugPrint('AuthNotifier: Google sign-in failed');
        return false;
      }
    } catch (e) {
      if (!ref.mounted) return false;
      debugPrint('AuthNotifier: Google sign-in error: $e');

      state = state.copyWith(
        isLoading: false,
        error: 'An error occurred during sign-in: ${e.toString()}',
      );

      return false;
    }
  }

  /// Sync the cached user's name after a successful profile PATCH so the
  /// greeting/profile header updates without a re-login.
  Future<void> updateUserName(String name) async {
    await _authService.updateCachedUserName(name);
    if (!ref.mounted) return;
    state = state.copyWith(user: _authService.currentUser);
  }

  /// Request a 6-digit sign-in code by email (mobile OTP flow).
  Future<bool> requestMagicCode(String email) async {
    state = state.copyWith(isLoading: true, clearError: true);
    final ok = await _authService.requestMagicCode(email);
    if (!ref.mounted) return ok;
    state = state.copyWith(
      isLoading: false,
      error: ok
          ? null
          : 'Could not send code. Check your connection and try again.',
    );
    return ok;
  }

  /// Verify a 6-digit OTP code and sign in.
  Future<bool> signInWithMagicCode({
    required String email,
    required String code,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final ok = await _authService.signInWithMagicCode(
        email: email,
        code: code,
      );
      if (!ref.mounted) return ok;
      if (!ok) {
        state = state.copyWith(
          isLoading: false,
          error: 'Invalid or expired code. Please try again.',
        );
        return false;
      }
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        user: _authService.currentUser,
        organizations: _authService.organizations,
        selectedOrganization: _authService.selectedOrganization,
      );
      return true;
    } catch (e) {
      if (!ref.mounted) return false;
      state = state.copyWith(
        isLoading: false,
        error: 'Sign-in failed: ${e.toString()}',
      );
      return false;
    }
  }

  /// Switch to a different organization
  Future<bool> switchOrganization(Organization org) async {
    debugPrint('AuthNotifier: Switching organization to ${org.name}...');

    state = state.copyWith(isLoading: true, clearError: true);

    try {
      final success = await _authService.selectOrganization(org);
      if (!ref.mounted) return success;

      if (success) {
        state = state.copyWith(isLoading: false, selectedOrganization: org);

        debugPrint('AuthNotifier: Organization switched to ${org.name}');
        return true;
      } else {
        state = state.copyWith(
          isLoading: false,
          error: 'Failed to switch organization',
        );

        return false;
      }
    } catch (e) {
      if (!ref.mounted) return false;
      debugPrint('AuthNotifier: Switch organization error: $e');

      state = state.copyWith(
        isLoading: false,
        error: 'An error occurred: ${e.toString()}',
      );

      return false;
    }
  }

  /// Create an organization, then move the session into it.
  ///
  /// Returns null on success, or a message to show. The org list and selected
  /// org both move, so the caller can navigate straight to the dashboard.
  Future<String?> createOrganization(String name, {String? timezone}) async {
    state = state.copyWith(isLoading: true, clearError: true);

    final failure = await _authService.createOrganization(
      name,
      timezone: timezone,
    );

    if (!ref.mounted) return failure;
    if (failure != null) {
      state = state.copyWith(isLoading: false, error: failure);
      return failure;
    }

    state = state.copyWith(
      isLoading: false,
      organizations: _authService.organizations,
      selectedOrganization: _authService.selectedOrganization,
    );
    return null;
  }

  /// Sign out
  Future<void> signOut() async {
    debugPrint('AuthNotifier: Signing out...');

    final pending = _authService.signOut();
    state = const AuthState.initial();
    await pending;

    debugPrint('AuthNotifier: Signed out');
  }

  /// Clear any error message
  void clearError() {
    state = state.copyWith(clearError: true);
  }
}

/// Provider for authentication state
final authProvider = NotifierProvider<AuthNotifier, AuthState>(
  AuthNotifier.new,
);

/// Provider for checking if user is authenticated
final isAuthenticatedProvider = Provider<bool>((ref) {
  return ref.watch(authProvider).isAuthenticated;
});

/// Provider for current user
final currentUserProvider = Provider<AuthUser?>((ref) {
  return ref.watch(authProvider).user;
});

/// Provider for selected organization
final selectedOrgProvider = Provider<Organization?>((ref) {
  return ref.watch(authProvider).selectedOrganization;
});

/// Role of the signed-in profile in the selected org, as an admin/not-admin
/// answer. The claim is server-issued and arrives with the org, so this reads
/// the same fact the backend's `is_org_admin` reads. UI affordances only; see
/// `core/permissions.dart`.
final isOrgAdminProvider = Provider<bool>((ref) {
  final org = ref.watch(selectedOrgProvider);
  return (org?.role ?? '').toUpperCase() == 'ADMIN';
});

/// The signed-in user's email, or null.
///
/// The one identifier this app and the API agree on for a person. Several
/// serializers surface an owner or author as an email rather than an id
/// (`User` carries no display name), so an ownership comparison in the UI has
/// to be made on this. UI affordances only; see `core/permissions.dart`.
final myEmailProvider = Provider<String?>((ref) {
  return ref.watch(authProvider).user?.email;
});

/// Provider for checking if org selection is needed
final needsOrgSelectionProvider = Provider<bool>((ref) {
  return ref.watch(authProvider).needsOrgSelection;
});
