// ═══════════════════════════════════════════════════════════════
// NormClaim — Supabase Browser Client Bootstrap
// Loads public runtime config from backend and initializes supabase-js.
// API_BASE is configurable via:
//   1. <meta name="nc-api-base" content="http://...">
//   2. URL query param ?api=http://...
//   3. Default: http://localhost:8000
// ═══════════════════════════════════════════════════════════════

(function () {
  function resolveApiBase() {
    // 1. <meta> tag override
    const metaTag = document.querySelector('meta[name="nc-api-base"]');
    if (metaTag?.content) return metaTag.content.replace(/\/+$/, '');

    // 2. URL query param override
    const params = new URLSearchParams(window.location.search);
    const paramBase = params.get('api');
    if (paramBase) return paramBase.replace(/\/+$/, '');

    // 3. Default
    return 'http://localhost:8000';
  }

  const API_BASE = resolveApiBase();

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
