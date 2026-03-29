// ═══════════════════════════════════════════════════════════════
// NormClaim — Auth Store & Role Management
// Primary: Supabase auth (real JWT tokens)
// Fallback: LocalDB for fully-offline demo mode
// ═══════════════════════════════════════════════════════════════

// Helper: determine if an error is an infrastructure/network issue
// (should fall back to LocalDB) vs a real user-facing auth error
// (should be shown to the user).
function _isSupabaseUnavailableError(msg) {
  if (!msg) return true;
  const m = msg.toLowerCase();
  return (
    m.includes('failed to fetch') ||       // Chrome/Firefox network error
    m.includes('load failed') ||            // Safari network error
    m.includes('networkerror') ||           // Generic network error
    m.includes('network request failed') || // React Native style
    m.includes('not loaded') ||             // SDK not loaded
    m.includes('not configured') ||         // Config missing
    m.includes('unable to load') ||         // Config endpoint down
    m.includes('supabase browser sdk')      // SDK missing
  );
}

const AuthStore = {
  _user: null,
  _listeners: [],
  _mode: 'unknown', // 'supabase' | 'local' | 'unknown'
  _initPromise: null,

  async init() {
    // Idempotent: return existing promise if already called
    if (this._initPromise) return this._initPromise;
    this._initPromise = this._doInit();
    return this._initPromise;
  },

  async _doInit() {
    // Try to restore a Supabase session first
    try {
      const client = await window.NormClaimSupabase?.getClient?.();
      if (client) {
        const { data: { session }, error } = await client.auth.getSession();
        if (session?.user && !error) {
          const meta = session.user.user_metadata || {};
          this._user = {
            id: session.user.id,
            email: session.user.email,
            name: meta.name || meta.full_name || session.user.email,
            role: meta.role || 'HOSPITAL',
            token: session.access_token,
          };
          this._mode = 'supabase';
          this._notify();

          // Listen for token refresh events
          client.auth.onAuthStateChange((event, newSession) => {
            if (event === 'TOKEN_REFRESHED' && newSession) {
              if (this._user) {
                this._user.token = newSession.access_token;
              }
            } else if (event === 'SIGNED_OUT') {
              this._user = null;
              this._mode = 'unknown';
              this._notify();
            }
          });
          return;
        }
      }
    } catch (e) {
      console.warn('[Auth] Supabase session restore failed, trying LocalDB:', e.message);
    }

    // Fallback: Restore from LocalDB (offline/demo mode)
    const session = LocalDB.getSession();
    if (session) {
      this._user = {
        id: session.userId,
        email: session.email,
        name: session.name,
        role: session.role,
        token: session.token,
      };
      this._mode = 'local';
    } else {
      this._user = null;
    }
    this._notify();
  },

  getUser() { return this._user; },
  getRole() { return this._user?.role || null; },
  isLoggedIn() { return !!this._user; },
  getAuthMode() { return this._mode; },

  // ── Login (email + password + role) ──────────────────────────
  async login({ email, password, role, name }) {
    // Try Supabase first
    try {
      const client = await window.NormClaimSupabase?.getClient?.();
      if (client) {
        const { data, error } = await client.auth.signInWithPassword({
          email: email.trim(),
          password,
        });

        if (error) throw new Error(error.message);

        const session = data.session;
        const user = data.user;
        const meta = user.user_metadata || {};

        // Determine role: prefer user_metadata.role, then the role selected in UI
        const userRole = meta.role || role || 'HOSPITAL';

        // If the user selected a role and it differs from stored, update metadata
        if (role && meta.role && role !== meta.role) {
          throw new Error('Selected role does not match your account role.');
        }

        this._user = {
          id: user.id,
          email: user.email,
          name: name || meta.name || meta.full_name || user.email,
          role: userRole,
          token: session.access_token,
        };
        this._mode = 'supabase';

        localStorage.setItem('nc_role', userRole);
        this._notify();
        return this._user;
      }
    } catch (e) {
      // Network/infrastructure error → fall back to LocalDB
      if (_isSupabaseUnavailableError(e.message)) {
        console.warn('[Auth] Supabase login unavailable, falling back to LocalDB:', e.message);
      } else {
        // Real auth error (wrong password, etc.) → show to user
        throw e;
      }
    }

    // Fallback: LocalDB sign-in (demo/offline mode)
    const session = LocalDB.signIn({ email, password });

    // Prevent client-side role escalation: selected role must match stored account role.
    if (role && role !== session.role) {
      throw new Error('Selected role does not match your account role.');
    }
    const finalRole = session.role;

    this._user = {
      id: session.userId,
      email: session.email,
      name: name || session.name,
      role: finalRole,
      token: session.token,
    };
    this._mode = 'local';

    localStorage.setItem('nc_role', finalRole);
    this._notify();
    return this._user;
  },

  // ── Sign Up (creates account + auto-signs-in) ───────────────
  async signUp({ email, password, name, role }) {
    // Try Supabase first
    try {
      const client = await window.NormClaimSupabase?.getClient?.();
      if (client) {
        const { data, error } = await client.auth.signUp({
          email: email.trim(),
          password,
          options: {
            data: {
              name: name.trim(),
              full_name: name.trim(),
              role: role || 'HOSPITAL',
            }
          }
        });

        if (error) throw new Error(error.message);

        // If email confirmation is required, user won't have a session yet
        if (!data.session) {
          throw new Error('Account created! Please check your email to confirm, then sign in.');
        }

        // Auto-signed-in after signup (confirmation disabled in Supabase)
        const session = data.session;
        const user = data.user;
        const meta = user.user_metadata || {};

        this._user = {
          id: user.id,
          email: user.email,
          name: meta.name || name.trim(),
          role: meta.role || role || 'HOSPITAL',
          token: session.access_token,
        };
        this._mode = 'supabase';

        localStorage.setItem('nc_role', this._user.role);
        this._notify();
        return this._user;
      }
    } catch (e) {
      // Network/infrastructure error → fall back to LocalDB
      if (_isSupabaseUnavailableError(e.message)) {
        console.warn('[Auth] Supabase signup unavailable, falling back to LocalDB:', e.message);
      } else {
        // Real auth error → show to user
        throw e;
      }
    }

    // Fallback: LocalDB
    LocalDB.signUp({ email, password, name, role });
    return this.login({ email, password, role, name });
  },

  // ── Logout ────────────────────────────────────────────────────
  async logout() {
    // Sign out of Supabase if we were using it
    if (this._mode === 'supabase') {
      try {
        const client = await window.NormClaimSupabase?.getClient?.();
        if (client) await client.auth.signOut();
      } catch (e) {
        console.warn('[Auth] Supabase sign-out error:', e.message);
      }
    }

    // Always clean up local state
    LocalDB.signOut();
    this._user = null;
    this._mode = 'unknown';
    localStorage.removeItem('nc_role');
    this._notify();
    Router.navigate('login');
  },

  subscribe(fn) { this._listeners.push(fn); },
  _notify() { this._listeners.forEach(fn => fn(this._user)); },

  hasAccess(requiredRole) {
    if (!this._user) return false;
    if (Array.isArray(requiredRole)) return requiredRole.includes(this._user.role);
    return this._user.role === requiredRole;
  },

  canAccessStage(stageNum) {
    if (!this._user) return false;
    return ROLE_META[this._user.role]?.stages.includes(stageNum) || false;
  }
};

// Kick off init (returns a Promise; app.html bootstrap awaits it)
AuthStore.init();

// Bridge for React auth overlay (auth-overlay.js) and tooling
window.NormClaimAuthBridge = {
  login: (args) => AuthStore.login(args),
  signUp: (args) => AuthStore.signUp(args),
};
