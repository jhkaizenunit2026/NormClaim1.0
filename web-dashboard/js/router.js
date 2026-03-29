// ═══════════════════════════════════════════════════════════════
// NormClaim — Hash-Based SPA Router
// ═══════════════════════════════════════════════════════════════

const Router = {
  _routes: {},
  _currentRoute: null,
  _container: null,

  init(containerId) {
    this._container = document.getElementById(containerId);
    window.addEventListener('hashchange', () => this._resolve());
    this._resolve();
  },

  register(path, handler, opts = {}) {
    this._routes[path] = { handler, ...opts };
  },

  navigate(path) {
    window.location.hash = '#/' + path.replace(/^#?\/?/, '');
  },

  getParam(name) {
    const hash = window.location.hash.slice(2); // remove #/
    const [path, qs] = hash.split('?');
    if (qs) {
      const params = new URLSearchParams(qs);
      return params.get(name);
    }
    return null;
  },

  // Extract path params like :claimId from pattern
  _matchRoute(hash) {
    for (const pattern in this._routes) {
      const regexStr = '^' + pattern.replace(/:([^/]+)/g, '([^/]+)') + '$';
      const match = hash.match(new RegExp(regexStr));
      if (match) {
        const paramNames = [...pattern.matchAll(/:([^/]+)/g)].map(m => m[1]);
        const params = {};
        paramNames.forEach((name, i) => params[name] = match[i + 1]);
        return { route: this._routes[pattern], params };
      }
    }
    return null;
  },

  _resolve() {
    const hash = (window.location.hash || '#/login').slice(2); // remove #/
    const [path] = hash.split('?');
    const matched = this._matchRoute(path);

    if (!matched) {
      this._render404();
      return;
    }

    const { route, params } = matched;

    // Role guard
    if (route.roles && !AuthStore.hasAccess(route.roles)) {
      if (!AuthStore.isLoggedIn()) {
        this.navigate('login');
      } else {
        this._renderUnauthorized();
      }
      return;
    }

    this._currentRoute = path;
    if (this._container) {
      this._container.innerHTML = '<div class="page-loading"><div class="spinner" style="width:32px;height:32px;border-width:3px;margin:40vh auto;"></div></div>';
    }

    try {
      const content = route.handler(params);
      if (this._container) {
        if (typeof content === 'string') {
          this._container.innerHTML = content;
        }
      }
    } catch (e) {
      console.error('Route error:', e);
      const message = e && e.message ? String(e.message) : 'Unknown error';
      this._container.innerHTML = `<div class="page-wrapper"><div class="empty-state"><h3>Error Loading Page</h3><p id="route-error-message"></p></div></div>`;
      const msgNode = document.getElementById('route-error-message');
      if (msgNode) msgNode.textContent = message;
    }
  },

  _render404() {
    if (this._container) {
      this._container.innerHTML = `
        <div class="page-wrapper" style="text-align:center;padding-top:20vh;">
          <h1 style="font-size:4rem;color:var(--text-muted);">404</h1>
          <p style="margin-bottom:var(--sp-6);">Page not found</p>
          <button class="btn btn-primary" onclick="Router.navigate('login')">Go Home</button>
        </div>`;
    }
  },

  _renderUnauthorized() {
    if (this._container) {
      this._container.innerHTML = `
        <div class="page-wrapper" style="text-align:center;padding-top:20vh;">
          <h1 style="font-size:2rem;color:var(--red-bright);">Access Denied</h1>
          <p style="margin-bottom:var(--sp-6);">You don't have permission to view this page.</p>
          <button class="btn btn-primary" onclick="Router.navigate('login')">Back to Login</button>
        </div>`;
    }
  }
};

window.Router = Router;
