// ═══════════════════════════════════════════════════════════════
// NormClaim — TPA Dashboard Components
// ═══════════════════════════════════════════════════════════════

const TPAComponents = {

  // ── Pre-Auth Queue (Stages 1+2) ───────────────────────────────
  PreAuthQueue() {
    setTimeout(() => TPAComponents._loadQueue(), 100);
    return `
      <div class="page-wrapper">
        <div class="page-header animate-in">
          <div class="eyebrow">TPA Dashboard</div>
          <h1>Pre-Auth Queue</h1>
          <p>Review and approve incoming pre-authorization requests from hospitals.</p>
        </div>
        <div class="stats-grid animate-in-delay-1" style="grid-template-columns:repeat(3,1fr);">
          <div class="stat-card-react" id="tq-pending" data-value="—" data-label="Pending Review"></div>
          <div class="stat-card-react" id="tq-approved" data-value="—" data-label="Today's Approvals"></div>
          <div class="stat-card-react" id="tq-rejected" data-value="—" data-label="Rejections"></div>
        </div>
        <div class="card animate-in-delay-2" style="padding:0;overflow:hidden;">
          <div style="padding:var(--sp-5) var(--sp-6);border-bottom:1px solid var(--border-subtle);background:var(--bg-elevated);display:flex;align-items:center;justify-content:space-between;">
            <h3 style="margin:0;">Incoming Requests</h3>
            <button class="btn btn-ghost btn-sm" onclick="TPAComponents._loadQueue()"><svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>Refresh</button>
          </div>
          <table><thead><tr><th>Claim ID</th><th>Patient</th><th>Hospital</th><th>Diagnosis</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead>
          <tbody id="tq-tbody"><tr><td colspan="7" style="text-align:center;padding:var(--sp-10);"><div class="spinner"></div></td></tr></tbody></table>
        </div>
      </div>`;
  },

  async _loadQueue() {
    let claims;
    try { claims = await Api.getClaims({ status: CLAIM_STATUS.PRE_AUTH_INITIATED }); } 
    catch(e) { claims = DEMO_CLAIMS.filter(c => c.status === CLAIM_STATUS.PRE_AUTH_INITIATED); }
    if (!claims.length) claims = DEMO_CLAIMS;

    if (window.__setStatCardValue) {
      window.__setStatCardValue('tq-pending', String(claims.filter(c => c.status === CLAIM_STATUS.PRE_AUTH_INITIATED).length));
      window.__setStatCardValue('tq-approved', String(claims.filter(c => c.status === CLAIM_STATUS.PRE_AUTH_APPROVED).length));
      window.__setStatCardValue('tq-rejected', '0');
    }

    const tbody = document.getElementById('tq-tbody');
    if (!tbody) return;
    tbody.innerHTML = claims.map(c => `
      <tr>
        <td><span class="font-mono text-teal" style="font-size:0.82rem;">${c.claimId}</span></td>
        <td><strong>${c.patientName}</strong></td>
        <td class="text-muted">${c.hospitalId || 'City General'}</td>
        <td>${c.diagnosis || '—'}</td>
        <td class="font-mono">${formatINR(c.preAuthAmount)}</td>
        <td>${SharedComponents.ClaimStatusBadge(c.status)}</td>
        <td><button class="btn btn-primary btn-sm" onclick="Router.navigate('tpa/review/${c.claimId}')">Review</button></td>
      </tr>
    `).join('');
  },

  // ── Review Decision Panel (Stages 1+2) ────────────────────────
  ReviewDecisionPanel(params) {
    const claimId = params.claimId;
    setTimeout(() => TPAComponents._loadReview(claimId), 100);
    return `
      <div class="page-wrapper">
        <div class="flex items-center gap-4 mb-6 animate-in">
          <button class="btn btn-ghost btn-sm" onclick="Router.navigate('tpa/queue')"><svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>Back to Queue</button>
          <h2 style="flex:1;">Review: ${claimId}</h2>
          <span id="rv-badge" class="badge badge-muted">loading</span>
        </div>
        <div id="rv-progress" class="mb-6 animate-in-delay-1"></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-6);">
          <div class="animate-in-delay-2">
            <div class="card" id="rv-patient"><div class="spinner" style="margin:var(--sp-8) auto;"></div></div>
            <div class="card mt-4" id="rv-docs"></div>
          </div>
          <div class="animate-in-delay-3">
            <div class="card">
              <h4 class="mb-4">Decision</h4>
              <div class="form-group"><label class="form-label">Approved Amount (₹)</label><input type="number" id="rv-amount" placeholder="Enter approved amount" /></div>
              <div class="form-group"><label class="form-label">Remarks</label><textarea id="rv-remarks" rows="3" placeholder="Add review notes..."></textarea></div>
              <div class="flex gap-3 mt-6">
                <button class="btn btn-primary btn-lg" style="flex:1;" onclick="TPAComponents._approvePreAuth('${claimId}')">
                  <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>Approve
                </button>
                <button class="btn btn-danger btn-lg" onclick="TPAComponents._rejectPreAuth('${claimId}')">Reject</button>
              </div>
            </div>
          </div>
        </div>
      </div>`;
  },

  async _loadReview(claimId) {
    let claim;
    try { claim = await Api.getClaim(claimId); } catch(e) { claim = DEMO_CLAIMS[0]; }
    const el = (id, val) => { const e = document.getElementById(id); if(e) e.innerHTML = val; };
    el('rv-badge', SharedComponents.ClaimStatusBadge(claim.status));
    el('rv-progress', SharedComponents.StageProgressBar(claim.status, ROLES.TPA));
    el('rv-patient', `
      <h4 class="mb-4">Patient Details</h4>
      <div class="summary-rows">
        <div class="summary-row"><span class="text-muted">Name</span><strong>${claim.patientName}</strong></div>
        <div class="summary-row"><span class="text-muted">Requested Amount</span><span class="font-mono" style="color:var(--gold);font-weight:600;">${formatINR(claim.preAuthAmount)}</span></div>
        <div class="summary-row"><span class="text-muted">Diagnosis</span><span>${claim.diagnosis || '—'}</span></div>
        <div class="summary-row"><span class="text-muted">Hospital</span><span>${claim.hospitalId || 'City General Hospital'}</span></div>
      </div>
    `);
    el('rv-docs', `<h4 class="mb-4">Attached Documents</h4><p class="text-muted" style="font-size:0.85rem;">Documents would be listed here from the API.</p>`);
    const amtInput = document.getElementById('rv-amount');
    if (amtInput) amtInput.value = claim.preAuthAmount || '';
  },

  async _approvePreAuth(claimId) {
    try {
      await Api.updateClaimStatus(claimId, CLAIM_STATUS.PRE_AUTH_APPROVED, { amount: document.getElementById('rv-amount')?.value });
    } catch(e) {}
    showToast('Pre-auth approved!', 'success');
    setTimeout(() => Router.navigate('tpa/queue'), 800);
  },

  async _rejectPreAuth(claimId) {
    showToast('Pre-auth rejected', 'warning');
    setTimeout(() => Router.navigate('tpa/queue'), 800);
  },

  // ── Discharge Approval Panel (Stage 7) ────────────────────────
  DischargeApprovalPanel(params) {
    const claimId = params.claimId;
    setTimeout(() => TPAComponents._loadDischargeReview(claimId), 100);
    return `
      <div class="page-wrapper">
        <div class="flex items-center gap-4 mb-6 animate-in">
          <button class="btn btn-ghost btn-sm" onclick="Router.navigate('tpa/cases')"><svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>Back</button>
          <h2 style="flex:1;">Discharge Approval: ${claimId}</h2>
          <div class="sla-timer" id="sla-timer" style="font-family:var(--font-mono);color:var(--gold);font-size:0.9rem;"></div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-6);">
          <div class="animate-in-delay-1">
            <div class="card" id="da-patient"><div class="spinner" style="margin:var(--sp-8) auto;"></div></div>
            <div class="card mt-4" id="da-docs"><h4 class="mb-4">Discharge Documents</h4><p class="text-muted">Loading documents...</p></div>
          </div>
          <div class="animate-in-delay-2">
            <div class="card">
              <h4 class="mb-4">Discharge Decision</h4>
              <div class="form-grid">
                <div class="form-group"><label class="form-label">Copay Amount (₹)</label><input type="number" id="da-copay" placeholder="0" /></div>
                <div class="form-group"><label class="form-label">TPA Payable (₹)</label><input type="number" id="da-payable" placeholder="Calculated" /></div>
              </div>
              <div class="form-group"><label class="form-label">Deductions (itemized)</label><textarea id="da-deductions" rows="3" placeholder="Line items..."></textarea></div>
              <div class="card-sm mt-3" style="background:var(--teal-faint);">
                <div style="font-size:0.78rem;color:var(--text-muted);">Formula: Pre-Auth + Enhancement - Copay - Deductions = TPA Payable</div>
                <div class="font-mono mt-2" id="da-formula" style="color:var(--teal-bright);font-size:0.85rem;">—</div>
              </div>
              <button class="btn btn-primary btn-lg w-full mt-4" onclick="TPAComponents._approveDischarge('${claimId}')">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>Approve Discharge
              </button>
            </div>
          </div>
        </div>
      </div>`;
  },

  async _loadDischargeReview(claimId) {
    let claim;
    try { claim = await Api.getClaim(claimId); } catch(e) { claim = DEMO_CLAIMS[2]; }
    const el = (id, val) => { const e = document.getElementById(id); if(e) e.innerHTML = val; };
    el('da-patient', `<h4 class="mb-4">Patient & Claim Summary</h4>
      <div class="summary-rows">
        <div class="summary-row"><span class="text-muted">Patient</span><strong>${claim.patientName}</strong></div>
        <div class="summary-row"><span class="text-muted">Admission #</span><span class="font-mono">${claim.admissionNumber || '—'}</span></div>
        <div class="summary-row"><span class="text-muted">Pre-Auth</span><span class="font-mono">${formatINR(claim.preAuthAmount)}</span></div>
        <div class="summary-row"><span class="text-muted">Enhancement</span><span class="font-mono">${formatINR(claim.enhancementAmount)}</span></div>
      </div>`);
    // SLA countdown
    if (claim.dischargeApprovalDeadline) {
      TPAComponents._startSLATimer(claim.dischargeApprovalDeadline);
    } else {
      const el2 = document.getElementById('sla-timer');
      if(el2) el2.innerHTML = '<span class="badge badge-gold">⏱ SLA: ~3 hours</span>';
    }
  },

  _startSLATimer(deadline) {
    const timer = document.getElementById('sla-timer');
    const update = () => {
      const diff = new Date(deadline) - new Date();
      if (diff <= 0) { if(timer) timer.innerHTML = '<span class="badge badge-red">⚠ SLA EXCEEDED</span>'; return; }
      const h = Math.floor(diff / 3600000); const m = Math.floor((diff % 3600000) / 60000); const s = Math.floor((diff % 60000) / 1000);
      if(timer) timer.textContent = `⏱ ${h}h ${m}m ${s}s remaining`;
    };
    update();
    setInterval(update, 1000);
  },

  async _approveDischarge(claimId) {
    try {
      await Api.updateClaimStatus(claimId, CLAIM_STATUS.DISCHARGE_APPROVED, {
        copay: document.getElementById('da-copay')?.value,
        payable: document.getElementById('da-payable')?.value,
      });
    } catch(e) {}
    showToast('Discharge approved!', 'success');
    setTimeout(() => Router.navigate('tpa/cases'), 800);
  },

  // ── TPA Cases ─────────────────────────────────────────────────
  AllCases() {
    setTimeout(() => TPAComponents._loadAllCases(), 100);
    return `
      <div class="page-wrapper">
        <div class="page-header animate-in">
          <div class="eyebrow">TPA Dashboard</div>
          <h1>All Cases</h1>
          <p>Complete case management across all 11 stages of the claim lifecycle.</p>
        </div>
        <div class="card animate-in-delay-1" style="padding:0;overflow:hidden;">
          <div style="padding:var(--sp-5) var(--sp-6);border-bottom:1px solid var(--border-subtle);background:var(--bg-elevated);display:flex;align-items:center;justify-content:space-between;">
            <h3 style="margin:0;">Case Management</h3>
            <select id="tc-filter" onchange="TPAComponents._loadAllCases()" style="width:auto;min-width:160px;">
              <option value="">All Stages</option>
              ${STATUS_ORDER.map(s => `<option value="${s}">${STAGE_META[s].label}</option>`).join('')}
            </select>
          </div>
          <table><thead><tr><th>Claim ID</th><th>Patient</th><th>Stage</th><th>Amount</th><th>Updated</th><th>Action</th></tr></thead>
          <tbody id="tc-tbody"><tr><td colspan="6" style="text-align:center;padding:var(--sp-10);"><div class="spinner"></div></td></tr></tbody></table>
        </div>
      </div>`;
  },

  async _loadAllCases() {
    let claims;
    try { claims = await Api.getClaims(); } catch(e) { claims = DEMO_CLAIMS; }
    const filter = document.getElementById('tc-filter')?.value;
    const filtered = filter ? claims.filter(c => c.status === filter) : claims;
    const tbody = document.getElementById('tc-tbody');
    if (!tbody) return;
    tbody.innerHTML = filtered.map(c => {
      const action = c.status === CLAIM_STATUS.PRE_AUTH_INITIATED ? `<button class="btn btn-primary btn-sm" onclick="Router.navigate('tpa/review/${c.claimId}')">Review</button>`
        : c.status === CLAIM_STATUS.DISCHARGE_INTIMATED ? `<button class="btn btn-gold btn-sm" onclick="Router.navigate('tpa/discharge/${c.claimId}')">Approve</button>`
        : `<button class="btn btn-ghost btn-sm" onclick="Router.navigate('tpa/review/${c.claimId}')">View</button>`;
      return `<tr>
        <td><span class="font-mono text-teal" style="font-size:0.82rem;">${c.claimId}</span></td>
        <td><strong>${c.patientName}</strong></td>
        <td>${SharedComponents.ClaimStatusBadge(c.status)}</td>
        <td class="font-mono">${formatINR(c.preAuthAmount)}</td>
        <td class="text-muted" style="font-size:0.82rem;">${formatDate(c.updatedAt)}</td>
        <td>${action}</td>
      </tr>`;
    }).join('');
  },
};
