// ═══════════════════════════════════════════════════════════════
// NormClaim — Shared UI Components
// Used by all roles: StageProgressBar, ClaimStatusBadge,
// DocumentUploader, AuditTrailTimeline, NotificationBell
// ═══════════════════════════════════════════════════════════════

const SharedComponents = {

  // ── Stage Progress Bar ────────────────────────────────────────
  StageProgressBar(currentStatus, role) {
    const stages = role === ROLES.FINANCE
      ? STATUS_ORDER.filter((_, i) => i >= 8) // Stages 9-11
      : STATUS_ORDER;

    const currentIdx = STATUS_ORDER.indexOf(currentStatus);
    return `
      <div class="stage-progress-bar">
        ${stages.map((s, i) => {
          const meta = STAGE_META[s];
          const globalIdx = STATUS_ORDER.indexOf(s);
          const isComplete = globalIdx < currentIdx;
          const isCurrent = globalIdx === currentIdx;
          const colors = STAGE_COLORS[meta.color];
          const cls = isComplete ? 'complete' : isCurrent ? 'current' : 'future';
          return `
            <div class="spb-step ${cls}" data-stage="${meta.stage}" 
                 style="--stage-color:${colors.solid};--stage-bg:${colors.bg};--stage-text:${colors.text}"
                 ${isComplete ? `onclick="Router.navigate('portal/claim/stage-${meta.stage}')"` : ''}>
              <div class="spb-dot">
                ${isComplete ? '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg>' : meta.stage}
              </div>
              <div class="spb-label">${meta.label}</div>
              ${i < stages.length - 1 ? '<div class="spb-connector"></div>' : ''}
            </div>`;
        }).join('')}
      </div>`;
  },

  // ── Claim Status Badge ────────────────────────────────────────
  ClaimStatusBadge(status) {
    const meta = STAGE_META[status];
    if (!meta) return `<span class="badge badge-muted">${status || 'Unknown'}</span>`;
    const colors = STAGE_COLORS[meta.color];
    return `<span class="badge" style="background:${colors.bg};color:${colors.text};border:1px solid ${colors.border}">${meta.label}</span>`;
  },

  // ── Notification Bell ─────────────────────────────────────────
  NotificationBell() {
    const count = NotificationStore.getUnreadCount();
    return `
      <div class="notif-bell" id="notifBell" onclick="SharedComponents._toggleNotifDropdown()">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
        </svg>
        ${count > 0 ? `<span class="notif-count">${count > 9 ? '9+' : count}</span>` : ''}
      </div>
      <div class="notif-dropdown" id="notifDropdown" style="display:none;">
        <div class="notif-dropdown-header">
          <span>Notifications</span>
          <button class="btn btn-ghost btn-sm" onclick="NotificationStore.markAllRead();SharedComponents._refreshNotifBell();">Mark all read</button>
        </div>
        <div class="notif-dropdown-list">
          ${NotificationStore.getAll().slice(0, 20).map(n => `
            <div class="notif-item ${n.read ? '' : 'unread'} ${n.priority}" onclick="${n.claimId ? `Router.navigate('portal/claim/${n.claimId}')` : ''}">
              <div class="notif-msg">${escapeHtml(n.message)}</div>
              <div class="notif-time">${formatDateTime(n.timestamp)}</div>
            </div>
          `).join('') || '<div class="notif-item"><div class="notif-msg text-muted">No notifications</div></div>'}
        </div>
      </div>`;
  },

  _toggleNotifDropdown() {
    const dd = document.getElementById('notifDropdown');
    dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
  },

  _refreshNotifBell() {
    const bell = document.getElementById('notifBell')?.parentElement;
    if (bell) bell.outerHTML = SharedComponents.NotificationBell();
  },

  // ── Audit Trail Timeline ──────────────────────────────────────
  AuditTrailTimeline(timeline = []) {
    if (!timeline.length) return '<p class="text-muted" style="font-size:0.85rem;">No audit trail available</p>';
    return `
      <div class="audit-timeline">
        ${timeline.map((entry, i) => {
          const meta = STAGE_META[entry.stage] || {};
          const colors = STAGE_COLORS[meta.color || 'gray'];
          return `
            <div class="audit-entry animate-in" style="animation-delay:${i * 50}ms">
              <div class="audit-dot" style="background:${colors.solid}"></div>
              <div class="audit-connector"></div>
              <div class="audit-content">
                <div class="audit-action">${entry.action || '—'}</div>
                <div class="audit-meta">
                  <span>${entry.actor || 'System'}</span>
                  <span class="badge" style="background:${colors.bg};color:${colors.text};font-size:0.6rem;padding:1px 6px;">${meta.label || entry.stage || ''}</span>
                  <span class="text-muted">${formatDateTime(entry.timestamp)}</span>
                </div>
              </div>
            </div>`;
        }).join('')}
      </div>`;
  },

  // ── Document Uploader ─────────────────────────────────────────
  DocumentUploader(claimId, stage, requiredDocs = [], onAllUploaded) {
    const uploaderId = 'uploader-' + Date.now();
    return `
      <div class="doc-uploader" id="${uploaderId}">
        <div class="doc-uploader-checklist">
          <div class="entity-section-title">Required Documents</div>
          ${requiredDocs.map((doc, i) => `
            <div class="doc-check-item" id="doc-check-${i}">
              <div class="doc-check-icon pending">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke-width="2"/></svg>
              </div>
              <span>${doc}</span>
            </div>
          `).join('')}
        </div>
        <div class="doc-upload-zone" id="${uploaderId}-zone"
             ondragover="event.preventDefault();this.classList.add('drag-over')"
             ondragleave="this.classList.remove('drag-over')"
             ondrop="event.preventDefault();this.classList.remove('drag-over');SharedComponents._handleDrop(event,'${claimId}','${uploaderId}')"
             onclick="document.getElementById('${uploaderId}-input').click()">
          <div class="upload-icon-sm">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
          </div>
          <div style="font-size:0.85rem;color:var(--text-secondary);">Drop files or <strong style="color:var(--teal-bright)">browse</strong></div>
          <div style="font-size:0.75rem;color:var(--text-muted);">PDF, JPG, PNG · Max 10MB</div>
        </div>
        <input type="file" id="${uploaderId}-input" accept=".pdf,.jpg,.jpeg,.png" class="sr-only" multiple
               onchange="SharedComponents._handleFiles(this.files,'${claimId}','${uploaderId}')" />
        <div class="doc-upload-list" id="${uploaderId}-list"></div>
      </div>`;
  },

  async _handleDrop(event, claimId, uploaderId) {
    const files = event.dataTransfer.files;
    await this._handleFiles(files, claimId, uploaderId);
  },

  async _handleFiles(files, claimId, uploaderId) {
    const list = document.getElementById(`${uploaderId}-list`);
    for (const file of files) {
      if (file.size > 10 * 1024 * 1024) { showToast(`${file.name} exceeds 10MB limit`, 'error'); continue; }
      if (!/\.(pdf|jpe?g|png)$/i.test(file.name)) { showToast(`${file.name}: invalid file type`, 'error'); continue; }
      const itemId = `upload-${Date.now()}`;
      list.innerHTML += `
        <div class="doc-upload-item" id="${itemId}">
          <span class="doc-upload-name">${file.name}</span>
          <div class="progress-bar-wrap" style="flex:1;max-width:120px;"><div class="progress-bar-fill" style="width:0%" id="${itemId}-bar"></div></div>
          <span class="doc-upload-status" id="${itemId}-status">Uploading…</span>
        </div>`;
      try {
        // Simulate progress then upload
        const bar = document.getElementById(`${itemId}-bar`);
        let pct = 0;
        const tick = setInterval(() => { pct = Math.min(pct + 15, 90); if(bar) bar.style.width = pct + '%'; }, 200);
        await Api.uploadDocument(claimId, file, file.name.split('.').pop());
        clearInterval(tick);
        if(bar) bar.style.width = '100%';
        const st = document.getElementById(`${itemId}-status`);
        if(st) { st.textContent = '✓ Done'; st.style.color = 'var(--green)'; }
        showToast(`${file.name} uploaded`, 'success');
      } catch(e) {
        const st = document.getElementById(`${itemId}-status`);
        if(st) { st.textContent = '✕ Failed'; st.style.color = 'var(--red-bright)'; }
      }
    }
  },

  // ── Top Navbar ────────────────────────────────────────────────
  Navbar() {
    const user = AuthStore.getUser();
    const role = user?.role;
    const roleMeta = role ? ROLE_META[role] : null;
    
    const links = !role ? '' : role === ROLES.HOSPITAL ? `
      <a href="#/portal/pre-auth/new" class="nav-link"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>New Pre-Auth</a>
      <a href="#/portal/cases" class="nav-link"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>My Cases</a>
    ` : role === ROLES.TPA ? `
      <a href="#/tpa/queue" class="nav-link"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>Queue</a>
      <a href="#/tpa/cases" class="nav-link"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>All Cases</a>
    ` : `
      <a href="#/finance/alerts" class="nav-link"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/></svg>Alerts</a>
      <a href="#/finance/ledger/entry" class="nav-link"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>Ledger</a>
      <a href="#/finance/reconciliation" class="nav-link"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>Reconciliation</a>
    `;

    return `
    <div class="nav-glass-shell" id="app-nav-inner">
      <nav class="nav nav-glass" aria-label="Main">
        <a href="#/login" class="nav-logo">
          <div class="nav-logo-mark">N</div>
          <span class="nav-logo-text">Norm<span>Claim</span></span>
        </a>
        <div class="nav-links">${links}</div>
        <div class="nav-spacer"></div>
        ${user ? `
          <div class="nav-notif-wrap">${SharedComponents.NotificationBell()}</div>
          <span class="nav-badge">${roleMeta?.icon || ''} ${roleMeta?.label || role}</span>
          <button type="button" class="btn btn-ghost btn-sm" onclick="AuthStore.logout()" aria-label="Log out">
            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
          </button>
        ` : '<span class="nc-flow-mount nc-flow-mount--nav" data-flow-mode="signin" data-flow-label="Sign In" aria-label="Sign In"></span>'}
      </nav>
    </div>`;
  }
};
