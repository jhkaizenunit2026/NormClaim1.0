// ═══════════════════════════════════════════════════════════════
// NormClaim — Local Database (localStorage-based)
// Self-contained user store — no backend dependency
// ═══════════════════════════════════════════════════════════════

const LocalDB = {
  _USERS_KEY: 'nc_local_users',
  _SESSION_KEY: 'nc_local_session',

  _getUsers() {
    try {
      return JSON.parse(localStorage.getItem(this._USERS_KEY)) || [];
    } catch { return []; }
  },

  _saveUsers(users) {
    localStorage.setItem(this._USERS_KEY, JSON.stringify(users));
  },

  // Seed default users on first run
  _ensureSeeded() {
    const users = this._getUsers();
    if (users.length > 0) return;

    const defaults = [
      { id: 'usr_001', email: 'hospital@normclaim.in', password: 'Hospital@123', name: 'Dr. Mehta',     role: 'HOSPITAL', createdAt: new Date().toISOString() },
      { id: 'usr_002', email: 'tpa@normclaim.in',      password: 'Tpa@1234',     name: 'Rahul Sharma',  role: 'TPA',      createdAt: new Date().toISOString() },
      { id: 'usr_003', email: 'finance@normclaim.in',   password: 'Finance@123',  name: 'Anita Kapoor',  role: 'FINANCE',  createdAt: new Date().toISOString() },
    ];
    this._saveUsers(defaults);
  },

  // ── Sign Up ────────────────────────────────────────────────
  signUp({ email, password, name, role }) {
    if (!email || !password || !name || !role) {
      throw new Error('All fields are required.');
    }
    if (password.length < 6) {
      throw new Error('Password must be at least 6 characters.');
    }
    if (!['HOSPITAL', 'TPA', 'FINANCE'].includes(role)) {
      throw new Error('Invalid role selected.');
    }

    const users = this._getUsers();
    const exists = users.find(u => u.email.toLowerCase() === email.toLowerCase());
    if (exists) {
      throw new Error('An account with this email already exists.');
    }

    const newUser = {
      id: 'usr_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      email: email.toLowerCase().trim(),
      password,       // In a real app we'd hash this
      name: name.trim(),
      role,
      createdAt: new Date().toISOString(),
    };

    users.push(newUser);
    this._saveUsers(users);
    return { id: newUser.id, email: newUser.email, name: newUser.name, role: newUser.role };
  },

  // ── Sign In ────────────────────────────────────────────────
  signIn({ email, password }) {
    if (!email || !password) {
      throw new Error('Email and password are required.');
    }

    this._ensureSeeded();

    const users = this._getUsers();
    const user = users.find(u => u.email.toLowerCase() === email.toLowerCase().trim());
    if (!user) {
      throw new Error('No account found with this email.');
    }
    if (user.password !== password) {
      throw new Error('Incorrect password.');
    }

    // Create session
    const session = {
      userId: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
      token: 'local_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
      loginAt: new Date().toISOString(),
    };
    localStorage.setItem(this._SESSION_KEY, JSON.stringify(session));
    return session;
  },

  // ── Restore Session ────────────────────────────────────────
  getSession() {
    try {
      const raw = localStorage.getItem(this._SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  },

  // ── Sign Out ───────────────────────────────────────────────
  signOut() {
    localStorage.removeItem(this._SESSION_KEY);
  },

  // ── List all users (for demo/admin) ────────────────────────
  listUsers() {
    return this._getUsers().map(u => ({
      id: u.id, email: u.email, name: u.name, role: u.role, createdAt: u.createdAt,
    }));
  }
};

// Seed defaults on load
LocalDB._ensureSeeded();
