// ═══════════════════════════════════════════════════════════════
// NormClaim — Auth Store & Role Management
// ═══════════════════════════════════════════════════════════════

const AuthStore = {
  _user: null,
  _listeners: [],

  init() {
    const saved = localStorage.getItem('nc_user');
    if (saved) {
      try { this._user = JSON.parse(saved); } catch(e) { this._user = null; }
    }
  },

  getUser() { return this._user; },
  getRole() { return this._user?.role || null; },
  isLoggedIn() { return !!this._user; },

  login(userData) {
    this._user = {
      role: userData.role,
      name: userData.name || 'User',
      hospitalId: userData.hospitalId || null,
      tpaOfficerId: userData.tpaOfficerId || null,
      financeUserId: userData.financeUserId || null,
      token: userData.token || 'demo-token',
    };
    localStorage.setItem('nc_user', JSON.stringify(this._user));
    this._notify();
  },

  logout() {
    this._user = null;
    localStorage.removeItem('nc_user');
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
