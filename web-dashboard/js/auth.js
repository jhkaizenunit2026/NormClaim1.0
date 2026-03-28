// ═══════════════════════════════════════════════════════════════
// NormClaim — Auth Store & Role Management
// Uses LocalDB for self-contained authentication (no backend)
// ═══════════════════════════════════════════════════════════════

const AuthStore = {
  _user: null,
  _listeners: [],

  init() {
    // Restore session from LocalDB
    const session = LocalDB.getSession();
    if (session) {
      this._user = {
        id: session.userId,
        email: session.email,
        name: session.name,
        role: session.role,
        token: session.token,
      };
    } else {
      this._user = null;
    }
    this._notify();
  },

  getUser() { return this._user; },
  getRole() { return this._user?.role || null; },
  isLoggedIn() { return !!this._user; },

  // ── Login (email + password + role) ──────────────────────────
  async login({ email, password, role, name }) {
    // First sign in to validate credentials
    const session = LocalDB.signIn({ email, password });

    // If a role was explicitly chosen, update the user's session role
    const finalRole = role || session.role;

    this._user = {
      id: session.userId,
      email: session.email,
      name: name || session.name,
      role: finalRole,
      token: session.token,
    };

    localStorage.setItem('nc_role', finalRole);
    this._notify();
    return this._user;
  },

  // ── Sign Up (creates account + auto-signs-in) ───────────────
  async signUp({ email, password, name, role }) {
    // Create the user
    LocalDB.signUp({ email, password, name, role });
    // Automatically sign them in
    return this.login({ email, password, role, name });
  },

  // ── Logout ────────────────────────────────────────────────────
  async logout() {
    LocalDB.signOut();
    this._user = null;
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

AuthStore.init();
