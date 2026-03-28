// ═══════════════════════════════════════════════════════════════
// NormClaim — Finance Panel Components (Stages 9-11)
// ═══════════════════════════════════════════════════════════════

const FinanceComponents = {

  // ── Finance Alerts (Stage 9) ──────────────────────────────────
  Alerts() {
    setTimeout(() => FinanceComponents._loadAlerts(), 100);
    return `
      <div class="page-wrapper">
        <div class="page-header animate-in">
          <div class="eyebrow">Finance Panel · Stage 9</div>
          <h1>Settlement Alerts</h1>
          <p>Pending UTR entries and settlement letters requiring finance team action.</p>
        </div>
        <div class="stats-grid animate-in-delay-1" style="grid-template-columns:repeat(3,1fr);">
          <div class="stat-card gold"><div class="stat-label">Pending Entries</div><div class="stat-value gold" id="fa-pending">—</div></div>
          <div class="stat-card green"><div class="stat-label">Processed Today</div><div class="stat-value green" id="fa-processed">—</div></div>
          <div class="stat-card teal"><div class="stat-label">Total Outstanding</div><div class="stat-value teal" id="fa-outstanding">—</div></div>
        </div>
        <div class="card animate-in-delay-2" style="padding:0;overflow:hidden;">
          <table><thead><tr><th>Claim ID</th><th>Patient</th><th>Settlement Amount</th><th>UTR</th><th>Status</th><th>Action</th></tr></thead>
          <tbody id="fa-tbody"><tr><td colspan="6" style="text-align:center;padding:var(--sp-10);"><div class="spinner"></div></td></tr></tbody></table>
        </div>
      </div>`;
  },

  async _loadAlerts() {
    let claims;
    try { claims = await Api.getClaims({ stage: 'settlement' }); } 
    catch(e) { claims = DEMO_CLAIMS.filter(c => isAtOrPast(c.status, CLAIM_STATUS.SETTLEMENT_ISSUED)); }
    if (!claims.length) claims = DEMO_CLAIMS.filter(c => isAtOrPast(c.status, CLAIM_STATUS.SETTLEMENT_ISSUED));

    const el = (id, v) => { const e = document.getElementById(id); if(e) e.textContent = v; };
    el('fa-pending', claims.filter(c => c.status === CLAIM_STATUS.SETTLEMENT_ISSUED).length);
    el('fa-processed', claims.filter(c => c.status === CLAIM_STATUS.FINANCE_PROCESSED).length);
    el('fa-outstanding', formatINR(claims.reduce((s, c) => s + (c.finalSettlementAmount || c.tpaPayableAmount || 0), 0)));

    const tbody = document.getElementById('fa-tbody');
    if (!tbody) return;
    tbody.innerHTML = claims.map(c => `
      <tr>
        <td><span class="font-mono text-teal" style="font-size:0.82rem;">${c.claimId}</span></td>
        <td><strong>${c.patientName}</strong></td>
        <td class="font-mono" style="color:var(--gold);font-weight:600;">${formatINR(c.finalSettlementAmount || c.tpaPayableAmount)}</td>
        <td class="font-mono">${c.utrNumber || '<span class="text-muted">Pending</span>'}</td>
        <td>${SharedComponents.ClaimStatusBadge(c.status)}</td>
        <td><button class="btn btn-primary btn-sm" onclick="Router.navigate('finance/ledger/entry/${c.claimId}')">Process</button></td>
      </tr>
    `).join('');
  },

  // ── Ledger Entry Form (Stage 10) ──────────────────────────────
  LedgerEntryForm(params) {
    const claimId = params?.claimId || 'new';
    setTimeout(() => FinanceComponents._loadLedgerData(claimId), 100);
    return `
      <div class="page-wrapper">
        <div class="flex items-center gap-4 mb-6 animate-in">
          <button class="btn btn-ghost btn-sm" onclick="Router.navigate('finance/alerts')"><svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>Back</button>
          <h2 style="flex:1;">Ledger Entry: ${claimId}</h2>
          <span class="badge badge-teal">Stage 10</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-6);">
          <div class="card animate-in-delay-1">
            <h4 class="mb-4">Entry Details</h4>
            <div class="form-grid">
              <div class="form-group">
                <label class="form-label">Account Number *</label>
                <select id="le-account"><option value="">Select account</option><option value="ACC-001">ACC-001 — Primary Settlement</option><option value="ACC-002">ACC-002 — Secondary</option><option value="ACC-003">ACC-003 — TDS Reserve</option></select>
              </div>
              <div class="form-group"><label class="form-label">Entry Date *</label><input type="date" id="le-date" /></div>
              <div class="form-group"><label class="form-label">Amount (₹) *</label><input type="number" id="le-amount" placeholder="Pre-filled from settlement" /></div>
              <div class="form-group"><label class="form-label">UTR Number</label><input type="text" id="le-utr" readonly class="font-mono" style="background:var(--bg-void);color:var(--teal-bright);" /></div>
              <div class="form-group"><label class="form-label">Bill Number</label><input type="text" id="le-bill" readonly class="font-mono" style="background:var(--bg-void);" /></div>
              <div class="form-group full-width"><label class="form-label">Remarks</label><textarea id="le-remarks" rows="3" placeholder="Optional notes..."></textarea></div>
            </div>
            <button class="btn btn-primary btn-lg w-full mt-4" onclick="FinanceComponents._submitLedger('${claimId}')">
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              Record Ledger Entry
            </button>
          </div>
          <div class="animate-in-delay-2">
            <div class="card" id="le-summary"><div class="spinner" style="margin:var(--sp-8) auto;"></div></div>
          </div>
        </div>
      </div>`;
  },

  async _loadLedgerData(claimId) {
    let claim;
    try { claim = await Api.getClaim(claimId); } catch(e) { claim = DEMO_CLAIMS.find(c => isAtOrPast(c.status, CLAIM_STATUS.SETTLEMENT_ISSUED)) || DEMO_CLAIMS[0]; }
    
    document.getElementById('le-date').value = new Date().toISOString().split('T')[0];
    document.getElementById('le-amount').value = claim.finalSettlementAmount || claim.tpaPayableAmount || '';
    document.getElementById('le-utr').value = claim.utrNumber || '';
    document.getElementById('le-bill').value = claim.billNumber || '';

    document.getElementById('le-summary').innerHTML = `
      <h4 class="mb-4">Claim Summary</h4>
      <div class="summary-rows">
        <div class="summary-row"><span class="text-muted">Patient</span><strong>${claim.patientName}</strong></div>
        <div class="summary-row"><span class="text-muted">Pre-Auth</span><span class="font-mono">${formatINR(claim.preAuthAmount)}</span></div>
        <div class="summary-row"><span class="text-muted">Enhancement</span><span class="font-mono">${formatINR(claim.enhancementAmount)}</span></div>
        <div class="summary-row"><span class="text-muted">Copay</span><span class="font-mono text-red">${formatINR(claim.copay)}</span></div>
        <div class="summary-row"><span class="text-muted">Deductions</span><span class="font-mono text-red">${formatINR(claim.deductions)}</span></div>
        <div class="summary-row" style="border-top:1px solid var(--border-subtle);padding-top:var(--sp-3);margin-top:var(--sp-2);">
          <span style="font-weight:600;">Final Settlement</span>
          <span class="font-mono" style="color:var(--green);font-weight:700;font-size:1.1rem;">${formatINR(claim.finalSettlementAmount || claim.tpaPayableAmount)}</span>
        </div>
        <div class="summary-row"><span class="text-muted">TDS</span><span class="font-mono">${formatINR(claim.tdsAmount)}</span></div>
      </div>`;
  },

  async _submitLedger(claimId) {
    const data = {
      account: document.getElementById('le-account')?.value,
      date: document.getElementById('le-date')?.value,
      amount: document.getElementById('le-amount')?.value,
      remarks: document.getElementById('le-remarks')?.value,
    };
    if (!data.account || !data.amount) { showToast('Please fill all required fields', 'error'); return; }
    try { await Api.recordFinanceEntry(claimId, data); } catch(e) {}
    showToast('Ledger entry recorded!', 'success');
    setTimeout(() => Router.navigate('finance/alerts'), 800);
  },

  // ── Reconciliation View (Stage 11) ────────────────────────────
  ReconciliationView() {
    setTimeout(() => FinanceComponents._loadRecon(), 100);
    return `
      <div class="page-wrapper">
        <div class="page-header animate-in">
          <div class="eyebrow">Finance Panel · Stage 11</div>
          <h1>Reconciliation</h1>
          <p>Final case reconciliation — verify payments, close settlements, and flag follow-ups.</p>
        </div>
        <div class="stats-grid animate-in-delay-1" style="grid-template-columns:repeat(4,1fr);">
          <div class="stat-card green"><div class="stat-label">Closed</div><div class="stat-value green" id="fr-closed">—</div></div>
          <div class="stat-card gold"><div class="stat-label">Pending Close</div><div class="stat-value gold" id="fr-pending">—</div></div>
          <div class="stat-card teal"><div class="stat-label">Total Settled</div><div class="stat-value teal" id="fr-total">—</div></div>
          <div class="stat-card red"><div class="stat-label">Follow-ups</div><div class="stat-value red" id="fr-followups">—</div></div>
        </div>
        <div class="card animate-in-delay-2" style="padding:0;overflow:hidden;">
          <table><thead><tr><th>Claim ID</th><th>Patient</th><th>Settlement</th><th>UTR</th><th>Status</th><th>Action</th></tr></thead>
          <tbody id="fr-tbody"><tr><td colspan="6" style="text-align:center;padding:var(--sp-10);"><div class="spinner"></div></td></tr></tbody></table>
        </div>
      </div>`;
  },

  async _loadRecon() {
    let claims;
    try { claims = await Api.getClaims(); } catch(e) { claims = DEMO_CLAIMS; }
    const finClaims = claims.filter(c => isAtOrPast(c.status, CLAIM_STATUS.FINANCE_PROCESSED));
    if (!finClaims.length) finClaims.push(...DEMO_CLAIMS.filter(c => isAtOrPast(c.status, CLAIM_STATUS.SETTLEMENT_ISSUED)));

    const el = (id, v) => { const e = document.getElementById(id); if(e) e.textContent = v; };
    el('fr-closed', finClaims.filter(c => c.status === CLAIM_STATUS.CLOSED).length);
    el('fr-pending', finClaims.filter(c => c.status !== CLAIM_STATUS.CLOSED).length);
    el('fr-total', formatINR(finClaims.reduce((s, c) => s + (c.finalSettlementAmount || 0), 0)));
    el('fr-followups', 0);

    const tbody = document.getElementById('fr-tbody');
    if (!tbody) return;
    tbody.innerHTML = finClaims.map(c => `
      <tr>
        <td><span class="font-mono text-teal" style="font-size:0.82rem;">${c.claimId}</span></td>
        <td><strong>${c.patientName}</strong></td>
        <td class="font-mono">${formatINR(c.finalSettlementAmount)}</td>
        <td class="font-mono">${c.utrNumber || '—'}</td>
        <td>${SharedComponents.ClaimStatusBadge(c.status)}</td>
        <td>${c.status !== CLAIM_STATUS.CLOSED 
          ? `<button class="btn btn-primary btn-sm" onclick="FinanceComponents._closeClaim('${c.claimId}')">Close Case</button>` 
          : '<span class="badge badge-green">✓ Closed</span>'}</td>
      </tr>
    `).join('');
  },

  async _closeClaim(claimId) {
    try { await Api.closeClaim(claimId); } catch(e) {}
    showToast('Case closed and archived', 'success');
    setTimeout(() => FinanceComponents._loadRecon(), 500);
  },
};
