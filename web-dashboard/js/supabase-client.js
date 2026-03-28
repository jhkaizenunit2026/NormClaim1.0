// ═══════════════════════════════════════════════════════════════
// NormClaim — Supabase Browser Client Bootstrap
// Loads public runtime config from backend and initializes supabase-js.
// ═══════════════════════════════════════════════════════════════

(function () {
  const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : 'http://localhost:8000';

  const Bridge = {
    _client: null,
    _config: null,
    _initPromise: null,

    getApiBase() {
      return API_BASE;
    },

    async init() {
      if (this._initPromise) return this._initPromise;

      this._initPromise = (async () => {
        if (!window.supabase || typeof window.supabase.createClient !== 'function') {
          throw new Error('Supabase browser SDK is not loaded.');
        }

        const res = await fetch(`${API_BASE}/api/config/public`);
        if (!res.ok) {
          throw new Error('Unable to load public runtime config.');
        }

        const cfg = await res.json();
        if (!cfg?.supabaseUrl || !cfg?.supabaseAnonKey) {
          throw new Error('Supabase public config is missing.');
        }

        this._config = cfg;
        this._client = window.supabase.createClient(cfg.supabaseUrl, cfg.supabaseAnonKey, {
          auth: {
            persistSession: true,
            autoRefreshToken: true,
            detectSessionInUrl: true,
          },
        });

        return this._client;
      })();

      return this._initPromise;
    },

    async getClient() {
      if (this._client) return this._client;
      return this.init();
    },
  };

  window.NormClaimSupabase = Bridge;
})();
