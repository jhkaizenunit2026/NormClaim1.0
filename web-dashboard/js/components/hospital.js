// ═══════════════════════════════════════════════════════════════
// NormClaim — Hospital Portal Components
// ═══════════════════════════════════════════════════════════════

const HospitalComponents = {

  // ── Pre-Auth Form (Stage 1) ───────────────────────────────────
  PreAuthForm() {
    return `
      <div class="page-wrapper">
        <div class="page-header animate-in">
          <div class="eyebrow">Stage 1 · Pre-Authorization</div>
          <h1>New Pre-Auth Request</h1>
          <p>Submit patient details, diagnosis, and supporting documents for pre-authorization approval.</p>
        </div>
        <div class="hero-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-6);">
          <div class="animate-in-delay-1">
            <div class="card">
              <h4 class="mb-4">Patient Information</h4>
              <div class="form-grid">
                <div class="form-group"><label class="form-label">Patient Name *</label><input type="text" id="pa-name" placeholder="Full name" /></div>
                <div class="form-group"><label class="form-label">Age *</label><input type="number" id="pa-age" placeholder="Years" /></div>
                <div class="form-group"><label class="form-label">Sex *</label><select id="pa-sex"><option value="">Select</option><option>Male</option><option>Female</option><option>Other</option></select></div>
                <div class="form-group"><label class="form-label">ABHA ID</label><input type="text" id="pa-abha" placeholder="XX-XXXX-XXXX-XXXX" /></div>
              </div>
              <h4 class="mb-4 mt-6">Diagnosis Details</h4>
              <div class="form-grid">
                <div class="form-group full-width"><label class="form-label">Primary Diagnosis *</label><input type="text" id="pa-diagnosis" placeholder="e.g. Community-acquired Pneumonia" /></div>
                <div class="form-group"><label class="form-label">ICD-10 Code</label><input type="text" id="pa-icd" placeholder="e.g. J18.9" class="font-mono" /></div>
                <div class="form-group"><label class="form-label">Estimated Amount (₹) *</label><input type="number" id="pa-amount" placeholder="e.g. 45000" /></div>
              </div>
              <h4 class="mb-4 mt-6">Referring Doctor</h4>
              <div class="form-grid">
                <div class="form-group"><label class="form-label">Doctor Name</label><input type="text" id="pa-doctor" placeholder="Dr. Name" /></div>
                <div class="form-group"><label class="form-label">Speciality</label><input type="text" id="pa-spec" placeholder="e.g. General Medicine" /></div>
              </div>
            </div>
          </div>
          <div class="animate-in-delay-2">
            <div class="card mb-4">
              <h4 class="mb-4">Supporting Documents</h4>
              ${SharedComponents.DocumentUploader('new', 'PRE_AUTH', REQUIRED_DOCS.PRE_AUTH)}
            </div>
            <div class="card" style="background:var(--teal-faint);border-color:var(--border-active);">
              <h4 class="mb-3 text-teal">Pre-Auth Checklist</h4>
              <div style="font-size:0.85rem;line-height:1.8;color:var(--text-secondary);">
                <div>☑ Valid patient identification</div>
                <div>☑ Medical diagnosis with ICD-10 code</div>
                <div>☑ Doctor referral letter</div>
                <div>☑ Estimated treatment cost</div>
                <div>☑ Insurance policy verification</div>
              </div>
            </div>
            <button class="btn btn-primary btn-lg w-full mt-4" onclick="HospitalComponents._submitPreAuth()" id="submitPreAuth">
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              Submit Pre-Authorization
            </button>
          </div>
        </div>
      </div>`;
  },

  async _submitPreAuth() {
    const data = {
      patientName: document.getElementById('pa-name')?.value,
      age: parseInt(document.getElementById('pa-age')?.value),
      sex: document.getElementById('pa-sex')?.value,
      abhaId: document.getElementById('pa-abha')?.value,
      diagnosis: document.getElementById('pa-diagnosis')?.value,
      icd10Code: document.getElementById('pa-icd')?.value,
      estimatedAmount: parseInt(document.getElementById('pa-amount')?.value),
      doctor: document.getElementById('pa-doctor')?.value,
    };
    if (!data.patientName || !data.diagnosis || !data.estimatedAmount) {
      showToast('Please fill all required fields', 'error'); return;
    }
    try {
      const result = await Api.createClaim(data);
      showToast('Pre-auth submitted successfully!', 'success');
      setTimeout(() => Router.navigate(`portal/pre-auth/${result.claimId || 'demo-001'}`), 1000);
    } catch(e) {
      showToast('Demo mode: Pre-auth created (ID: DEMO-001)', 'success');
      setTimeout(() => Router.navigate('portal/cases'), 1000);
    }
  },

  // ── Cases Dashboard ───────────────────────────────────────────
  CasesDashboard() {
    setTimeout(() => HospitalComponents._loadCases(), 100);
    return `
      <div class="page-wrapper">
        <div class="page-header animate-in">
          <div class="eyebrow">Hospital Portal</div>
          <h1>My Cases</h1>
          <p>Track all claims from pre-authorization through settlement and closure.</p>
        </div>
        <div class="stats-grid animate-in-delay-1" style="grid-template-columns:repeat(4,1fr);">
          <div class="stat-card-react" id="cs-active" data-value="—" data-label="Active Cases"></div>
          <div class="stat-card-react" id="cs-pending" data-value="—" data-label="Pending Approval"></div>
          <div class="stat-card-react" id="cs-settled" data-value="—" data-label="Settled"></div>
          <div class="stat-card-react" id="cs-value" data-value="—" data-label="Total Value"></div>
        </div>
        <div class="card animate-in-delay-2" style="padding:0;overflow:hidden;">
          <div style="display:flex;align-items:center;justify-content:space-between;padding:var(--sp-5) var(--sp-6);border-bottom:1px solid var(--border-subtle);background:var(--bg-elevated);">
            <h3 style="margin:0;">All Claims</h3>
            <div class="flex gap-2">
              <select id="cs-filter" onchange="HospitalComponents._loadCases()" style="width:auto;min-width:160px;">
                <option value="">All Statuses</option>
                ${STATUS_ORDER.map(s => `<option value="${s}">${STAGE_META[s].label}</option>`).join('')}
              </select>
              <button class="btn btn-primary btn-sm" onclick="Router.navigate('portal/pre-auth/new')">+ New Pre-Auth</button>
            </div>
          </div>
          <table><thead><tr><th>Claim ID</th><th>Patient</th><th>Status</th><th>Amount</th><th>Updated</th><th></th></tr></thead>
          <tbody id="cases-tbody"><tr><td colspan="6" style="text-align:center;padding:var(--sp-10);"><div class="spinner"></div></td></tr></tbody></table>
        </div>
      </div>`;
  },

  async _loadCases() {
    try {
      const claims = await Api.getClaims();
      HospitalComponents._renderCases(claims);
    } catch(e) {
      HospitalComponents._renderCases(DEMO_CLAIMS);
    }
  },

  _renderCases(claims) {
    const filter = document.getElementById('cs-filter')?.value;
    const filtered = filter ? claims.filter(c => c.status === filter) : claims;
    
    // Stats
    const active = claims.filter(c => !isAtOrPast(c.status, CLAIM_STATUS.CLOSED)).length;
    const pending = claims.filter(c => [CLAIM_STATUS.PRE_AUTH_INITIATED, CLAIM_STATUS.ENHANCEMENT_REQUESTED, CLAIM_STATUS.DISCHARGE_INTIMATED].includes(c.status)).length;
    const settled = claims.filter(c => isAtOrPast(c.status, CLAIM_STATUS.SETTLEMENT_ISSUED)).length;
    const totalVal = claims.reduce((s, c) => s + (c.preAuthAmount || 0), 0);
    
    if (window.__setStatCardValue) {
      window.__setStatCardValue('cs-active', String(active));
      window.__setStatCardValue('cs-pending', String(pending));
      window.__setStatCardValue('cs-settled', String(settled));
      window.__setStatCardValue('cs-value', formatINR(totalVal));
    }
    
    const tbody = document.getElementById('cases-tbody');
    if (!tbody) return;
    if (!filtered.length) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><h3>No cases found</h3><p>Create a new pre-auth request to get started</p></div></td></tr>';
      return;
    }
    tbody.innerHTML = filtered.map(c => `
      <tr style="cursor:pointer" onclick="Router.navigate('portal/claim/${c.claimId}')">
        <td><span class="font-mono" style="color:var(--teal-bright);font-size:0.82rem;">${c.claimId}</span></td>
        <td><strong>${c.patientName}</strong></td>
        <td>${SharedComponents.ClaimStatusBadge(c.status)}</td>
        <td class="font-mono">${formatINR(c.preAuthAmount)}</td>
        <td class="text-muted" style="font-size:0.82rem;">${formatDate(c.updatedAt)}</td>
        <td><svg width="16" height="16" fill="none" stroke="var(--text-muted)" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg></td>
      </tr>
    `).join('');
  },

  // ── Claim Detail View ─────────────────────────────────────────
  ClaimDetail(params) {
    const claimId = params.claimId;
    setTimeout(() => HospitalComponents._loadClaimDetail(claimId), 100);
    return `
      <div class="page-wrapper">
        <div class="flex items-center gap-4 mb-6 animate-in">
          <button class="btn btn-ghost btn-sm" onclick="Router.navigate('portal/cases')"><svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>Back</button>
          <div style="flex:1;"><h2 id="cd-title">Claim ${claimId}</h2></div>
          <span id="cd-badge" class="badge badge-muted">loading…</span>
        </div>
        <div id="cd-progress" class="mb-8 animate-in-delay-1"></div>
        <div class="hero-grid" style="display:grid;grid-template-columns:2fr 1fr;gap:var(--sp-6);">
          <div id="cd-main" class="animate-in-delay-2"><div class="card"><div class="spinner" style="margin:var(--sp-10) auto;"></div></div></div>
          <div id="cd-sidebar" class="animate-in-delay-3"></div>
        </div>
        <div class="card mt-6 animate-in-delay-4">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--sp-4);">
            <h4>Audit Trail</h4>
            <button class="btn btn-ghost btn-sm" onclick="document.getElementById('cd-timeline').classList.toggle('hidden')">Toggle</button>
          </div>
          <div id="cd-timeline"></div>
        </div>
      </div>`;
  },

  async _loadClaimDetail(claimId) {
    let claim;
    try {
      claim = await Api.getClaim(claimId);
    } catch(e) {
      claim = DEMO_CLAIMS.find(c => c.claimId === claimId) || DEMO_CLAIMS[0];
    }
    SocketManager.joinClaimRoom(claimId);

    const meta = STAGE_META[claim.status] || {};
    const el = (id, val) => { const e = document.getElementById(id); if(e) { if(typeof val === 'string') e.innerHTML = val; else e.textContent = val; }};
    
    el('cd-title', `${claim.patientName || 'Patient'} — ${meta.label || claim.status}`);
    el('cd-badge', SharedComponents.ClaimStatusBadge(claim.status));
    el('cd-progress', SharedComponents.StageProgressBar(claim.status, ROLES.HOSPITAL));
    el('cd-timeline', SharedComponents.AuditTrailTimeline(claim.timeline || DEMO_TIMELINE));

    // Main content - shows relevant stage info
    const stageContent = HospitalComponents._getStageContent(claim);
    el('cd-main', stageContent);

    // Sidebar
    el('cd-sidebar', `
      <div class="card mb-4">
        <h4 class="mb-4">Claim Summary</h4>
        <div class="summary-rows">
          <div class="summary-row"><span class="text-muted">Claim ID</span><span class="font-mono text-teal">${claim.claimId}</span></div>
          <div class="summary-row"><span class="text-muted">Admission #</span><span>${claim.admissionNumber || '—'}</span></div>
          <div class="summary-row"><span class="text-muted">Pre-Auth Amount</span><span class="font-mono">${formatINR(claim.preAuthAmount)}</span></div>
          <div class="summary-row"><span class="text-muted">Enhancement</span><span class="font-mono">${formatINR(claim.enhancementAmount)}</span></div>
          <div class="summary-row"><span class="text-muted">Copay</span><span class="font-mono">${formatINR(claim.copay)}</span></div>
          <div class="summary-row"><span class="text-muted">Deductions</span><span class="font-mono">${formatINR(claim.deductions)}</span></div>
          <div class="summary-row"><span class="text-muted">TPA Payable</span><span class="font-mono" style="color:var(--green);font-weight:600;">${formatINR(claim.tpaPayableAmount)}</span></div>
          <div class="summary-row"><span class="text-muted">UTR Number</span><span class="font-mono">${claim.utrNumber || '—'}</span></div>
        </div>
      </div>
      <div class="card" style="background:var(--teal-faint);border-color:var(--border-active);">
        <h4 class="mb-3 text-teal">Next Steps</h4>
        <p style="font-size:0.85rem;line-height:1.7;">${HospitalComponents._getNextSteps(claim.status)}</p>
      </div>
    `);
  },

  _getStageContent(claim) {
    const st = claim.status;
    if (st === CLAIM_STATUS.PRE_AUTH_INITIATED) return `<div class="card"><h3 class="mb-4">Pre-Auth Submitted</h3><p>Your pre-authorization request is under review by the TPA. You'll be notified once a decision is made.</p><div class="card-sm mt-4" style="background:var(--gold-faint);"><span class="badge badge-gold">⏳ Awaiting TPA Review</span></div></div>`;
    if (st === CLAIM_STATUS.PRE_AUTH_APPROVED) return `<div class="card"><h3 class="mb-4">Pre-Auth Approved</h3><p>Amount approved: <strong style="color:var(--green);font-size:1.2rem;">${formatINR(claim.preAuthAmount)}</strong></p><button class="btn btn-primary mt-4" onclick="Router.navigate('portal/admission/${claim.claimId}')">Proceed to Admission</button></div>`;
    if (st === CLAIM_STATUS.ADMITTED) return `<div class="card"><h3 class="mb-4">Patient Admitted</h3><p>Admission Number: <strong class="font-mono text-teal" style="font-size:1.1rem;">${claim.admissionNumber || 'ADM-' + claim.claimId}</strong></p><div class="flex gap-3 mt-4"><button class="btn btn-gold" onclick="Router.navigate('portal/enhancement/${claim.claimId}')">Request Enhancement</button><button class="btn btn-primary" onclick="Router.navigate('portal/discharge/${claim.claimId}')">Initiate Discharge</button></div></div>`;
    if (st === CLAIM_STATUS.DISCHARGE_INTIMATED) return `<div class="card"><h3 class="mb-4">Discharge Documents Submitted</h3><p>The TPA is reviewing your discharge documents. SLA: ~3 hours from submission.</p>${claim.dischargeApprovalDeadline ? `<div class="card-sm mt-4" style="background:var(--gold-faint);"><span class="text-gold font-mono">Deadline: ${formatDateTime(claim.dischargeApprovalDeadline)}</span></div>` : ''}</div>`;
    if (st === CLAIM_STATUS.DISCHARGE_APPROVED) return `<div class="card"><h3 class="mb-4">Discharge Approved</h3><div class="stats-grid" style="grid-template-columns:1fr 1fr 1fr;"><div class="stat-card-react" data-value="${formatINR(claim.copay)}" data-label="Copay"></div><div class="stat-card-react" data-value="${formatINR(claim.deductions)}" data-label="Deductions"></div><div class="stat-card-react" data-value="${formatINR(claim.tpaPayableAmount)}" data-label="TPA Payable"></div></div></div>`;
    if (st === CLAIM_STATUS.SETTLEMENT_ISSUED) return `<div class="card"><h3 class="mb-4">Settlement Issued</h3><p>Final settlement: <strong style="color:var(--green);font-size:1.3rem;">${formatINR(claim.finalSettlementAmount)}</strong></p><p class="mt-2 text-muted">UTR: ${claim.utrNumber || 'Pending'} | TDS: ${formatINR(claim.tdsAmount)}</p></div>`;
    if (st === CLAIM_STATUS.CLOSED) return `<div class="card" style="background:var(--green-faint);border-color:rgba(46,201,138,0.3);"><h3 class="mb-4" style="color:var(--green);">✓ Case Closed</h3><p>This case has been settled and closed. All payments have been processed.</p></div>`;
    return `<div class="card"><h3 class="mb-4">${STAGE_META[st]?.label || st}</h3><p>Claim is being processed at this stage.</p></div>`;
  },

  _getNextSteps(status) {
    const steps = {
      [CLAIM_STATUS.PRE_AUTH_INITIATED]: 'Wait for TPA approval. You can upload additional documents in the meantime.',
      [CLAIM_STATUS.PRE_AUTH_APPROVED]: 'Proceed with patient admission and record the admission number.',
      [CLAIM_STATUS.ADMITTED]: 'Patient is admitted. Request enhancement if more funds needed, or initiate discharge when ready.',
      [CLAIM_STATUS.ENHANCEMENT_REQUESTED]: 'Enhancement request under TPA review.',
      [CLAIM_STATUS.ENHANCEMENT_APPROVED]: 'Additional funds approved. Continue treatment or initiate discharge.',
      [CLAIM_STATUS.DISCHARGE_INTIMATED]: 'TPA is reviewing discharge documents (~3 hour SLA).',
      [CLAIM_STATUS.DISCHARGE_APPROVED]: 'Complete patient discharge and mail hard copies.',
      [CLAIM_STATUS.DISCHARGE_COMPLETE]: 'Settlement letter will be generated by TPA.',
      [CLAIM_STATUS.SETTLEMENT_ISSUED]: 'Finance team will process the payment.',
      [CLAIM_STATUS.FINANCE_PROCESSED]: 'Payment is being finalized. UTR tracking in progress.',
      [CLAIM_STATUS.CLOSED]: 'Case is closed. No further action needed.',
    };
    return steps[status] || 'Processing...';
  },
};
