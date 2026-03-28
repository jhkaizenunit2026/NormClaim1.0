// ═══════════════════════════════════════════════════════════════
// NormClaim — Auth Store & Role Management
// ═══════════════════════════════════════════════════════════════

const AuthStore = {
  _user: null,
  _listeners: [],

  async init() {
    try {
      const sb = await window.NormClaimSupabase.getClient();
      const { data, error } = await sb.auth.getSession();
      if (error) throw error;

      const session = data?.session || null;
      if (!session) {
        this._user = null;
        localStorage.removeItem('nc_user');
        this._notify();
        return;
      }

      const role = localStorage.getItem('nc_role') || session.user?.user_metadata?.role || ROLES.HOSPITAL;
      this._user = {
        id: session.user?.id,
        email: session.user?.email,
        name: session.user?.user_metadata?.name || session.user?.email || 'User',
        role,
        token: session.access_token,
      };

      localStorage.setItem('nc_user', JSON.stringify(this._user));
      this._notify();
    } catch (e) {
      this._user = null;
      localStorage.removeItem('nc_user');
      this._notify();
    }
  },

  getUser() { return this._user; },
  getRole() { return this._user?.role || null; },
  isLoggedIn() { return !!this._user; },

  async login(userData) {
    const sb = await window.NormClaimSupabase.getClient();
    const { data, error } = await sb.auth.signInWithPassword({
      email: userData.email,
      password: userData.password,
    });
    if (error) throw error;

    const session = data?.session;
    if (!session) {
      throw new Error('Supabase session was not created.');
    }

    this._user = {
      id: session.user?.id,
      email: session.user?.email,
      role: userData.role,
      name: userData.name || session.user?.email || 'User',
      token: session.access_token,
    };

    localStorage.setItem('nc_role', userData.role);
    localStorage.setItem('nc_user', JSON.stringify(this._user));
    this._notify();
    return this._user;
  },

  async logout() {
    try {
      const sb = await window.NormClaimSupabase.getClient();
      await sb.auth.signOut();
    } catch (e) {
      // Ignore sign-out race/network errors and clear local session regardless.
    }
    this._user = null;
    localStorage.removeItem('nc_user');
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
