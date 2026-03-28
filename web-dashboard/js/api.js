// ═══════════════════════════════════════════════════════════════
// NormClaim — API Service Layer
// ═══════════════════════════════════════════════════════════════

const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000' : 'http://localhost:8000';

const Api = {
  _getHeaders() {
    const h = { 'Content-Type': 'application/json' };
    const user = AuthStore.getUser();
    if (user?.token) h['Authorization'] = `Bearer ${user.token}`;
    return h;
  },

  async _fetch(url, opts = {}) {
    const retries = opts.retries ?? 2;
    for (let i = 0; i <= retries; i++) {
      try {
        const res = await fetch(`${API_BASE}${url}`, {
          headers: this._getHeaders(),
          ...opts,
          headers: { ...this._getHeaders(), ...(opts.headers || {}) },
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return await res.json();
      } catch (e) {
        if (i === retries) throw e;
        await new Promise(r => setTimeout(r, 500 * (i + 1)));
      }
    }
  },

  // Claims
  getClaims(filters = {}) {
    const qs = new URLSearchParams(filters).toString();
    return this._fetch(`/api/claims${qs ? '?' + qs : ''}`);
  },
  getClaim(claimId) { return this._fetch(`/api/claims/${claimId}`); },
  createClaim(data) { return this._fetch('/api/claims', { method: 'POST', body: JSON.stringify(data) }); },
  updateClaimStatus(claimId, status, data = {}) {
    return this._fetch(`/api/claims/${claimId}/status`, { method: 'PATCH', body: JSON.stringify({ status, ...data }) });
  },

  // Enhancement
  submitEnhancement(claimId, data) {
    return this._fetch(`/api/claims/${claimId}/enhancement`, { method: 'POST', body: JSON.stringify(data) });
  },

  // Discharge
  submitDischarge(claimId, data) {
    return this._fetch(`/api/claims/${claimId}/discharge`, { method: 'POST', body: JSON.stringify(data) });
  },

  // Documents
  getDocuments(claimId) { return this._fetch(`/api/claims/${claimId}/documents`); },
  uploadDocument(claimId, file, docType) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('type', docType);
    return fetch(`${API_BASE}/api/claims/${claimId}/documents`, {
      method: 'POST', body: fd,
      headers: { 'Authorization': `Bearer ${AuthStore.getUser()?.token}` }
    }).then(r => r.json());
  },

  // Settlement
  issueSettlement(claimId, data) {
    return this._fetch(`/api/claims/${claimId}/settlement`, { method: 'POST', body: JSON.stringify(data) });
  },

  // Finance
  recordFinanceEntry(claimId, data) {
    return this._fetch(`/api/claims/${claimId}/finance-entry`, { method: 'POST', body: JSON.stringify(data) });
  },

  // Close
  closeClaim(claimId) {
    return this._fetch(`/api/claims/${claimId}/close`, { method: 'POST' });
  },

  // Notifications
  getNotifications() { return this._fetch('/api/notifications'); },

  // Legacy endpoints (from old dashboard)
  getOldDocuments() { return this._fetch('/api/documents'); },
  getAnalytics() { return this._fetch('/api/analytics'); },
};
