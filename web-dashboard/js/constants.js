// ═══════════════════════════════════════════════════════════════
// NormClaim — Claim Status State Machine & Constants
// Source of truth for all UI rendering decisions
// ═══════════════════════════════════════════════════════════════

const CLAIM_STATUS = Object.freeze({
  PRE_AUTH_INITIATED:    'PRE_AUTH_INITIATED',
  PRE_AUTH_APPROVED:     'PRE_AUTH_APPROVED',
  ADMITTED:              'ADMITTED',
  ENHANCEMENT_REQUESTED: 'ENHANCEMENT_REQUESTED',
  ENHANCEMENT_APPROVED:  'ENHANCEMENT_APPROVED',
  DISCHARGE_INTIMATED:   'DISCHARGE_INTIMATED',
  DISCHARGE_APPROVED:    'DISCHARGE_APPROVED',
  DISCHARGE_COMPLETE:    'DISCHARGE_COMPLETE',
  SETTLEMENT_ISSUED:     'SETTLEMENT_ISSUED',
  FINANCE_PROCESSED:     'FINANCE_PROCESSED',
  CLOSED:                'CLOSED',
});

const STATUS_ORDER = Object.values(CLAIM_STATUS);

function isAtOrPast(current, target) {
  return STATUS_ORDER.indexOf(current) >= STATUS_ORDER.indexOf(target);
}

function getStageNumber(status) {
  return STATUS_ORDER.indexOf(status) + 1;
}

// Stage metadata with colors matching the master prompt spec
const STAGE_META = {
  [CLAIM_STATUS.PRE_AUTH_INITIATED]:    { stage: 1,  label: 'Pre-Auth Initiated',    group: 'preauth',     color: 'teal' },
  [CLAIM_STATUS.PRE_AUTH_APPROVED]:     { stage: 2,  label: 'Pre-Auth Approved',      group: 'preauth',     color: 'teal' },
  [CLAIM_STATUS.ADMITTED]:              { stage: 3,  label: 'Admitted',               group: 'preauth',     color: 'teal' },
  [CLAIM_STATUS.ENHANCEMENT_REQUESTED]: { stage: 4,  label: 'Enhancement Requested',  group: 'enhancement', color: 'amber' },
  [CLAIM_STATUS.ENHANCEMENT_APPROVED]:  { stage: 5,  label: 'Enhancement Approved',   group: 'enhancement', color: 'amber' },
  [CLAIM_STATUS.DISCHARGE_INTIMATED]:   { stage: 6,  label: 'Discharge Intimated',    group: 'discharge',   color: 'coral' },
  [CLAIM_STATUS.DISCHARGE_APPROVED]:    { stage: 7,  label: 'Discharge Approved',     group: 'discharge',   color: 'coral' },
  [CLAIM_STATUS.DISCHARGE_COMPLETE]:    { stage: 8,  label: 'Discharge Complete',     group: 'discharge',   color: 'coral' },
  [CLAIM_STATUS.SETTLEMENT_ISSUED]:     { stage: 9,  label: 'Settlement Issued',      group: 'settlement',  color: 'blue' },
  [CLAIM_STATUS.FINANCE_PROCESSED]:     { stage: 10, label: 'Finance Processed',      group: 'settlement',  color: 'blue' },
  [CLAIM_STATUS.CLOSED]:                { stage: 11, label: 'Closed',                 group: 'closed',      color: 'green' },
};

const STAGE_COLORS = {
  teal:  { bg: 'rgba(2,128,144,0.12)', border: 'rgba(2,128,144,0.4)', text: '#03a3b8', solid: '#028090' },
  amber: { bg: 'rgba(245,166,35,0.12)', border: 'rgba(245,166,35,0.4)', text: '#ffc14d', solid: '#F5A623' },
  coral: { bg: 'rgba(224,92,75,0.12)', border: 'rgba(224,92,75,0.4)', text: '#f0705f', solid: '#E05C4B' },
  blue:  { bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.4)', text: '#60a5fa', solid: '#3b82f6' },
  green: { bg: 'rgba(46,201,138,0.12)', border: 'rgba(46,201,138,0.4)', text: '#2ec98a', solid: '#2ec98a' },
  gray:  { bg: 'rgba(61,100,120,0.12)', border: 'rgba(61,100,120,0.4)', text: '#7fa8c0', solid: '#3d6478' },
};

const ROLES = Object.freeze({
  HOSPITAL: 'HOSPITAL',
  TPA:      'TPA',
  FINANCE:  'FINANCE',
});

const ROLE_META = {
  [ROLES.HOSPITAL]: { label: 'Hospital Portal', icon: '🏥', stages: [1,2,3,4,5,6,7,8,9,10,11] },
  [ROLES.TPA]:      { label: 'TPA Dashboard',   icon: '📋', stages: [1,2,3,4,5,6,7,8,9,10,11] },
  [ROLES.FINANCE]:  { label: 'Finance Panel',   icon: '💰', stages: [9,10,11] },
};

// Document requirements per stage
const REQUIRED_DOCS = {
  PRE_AUTH: ['ID Proof', 'Diagnosis Report', 'Referral Letter', 'Pre-Auth Form'],
  DISCHARGE: ['Discharge Summary', 'Final Bill', 'ICPs', 'Internal Case Papers'],
};

// INR formatter
function formatINR(amount) {
  if (amount == null) return '—';
  return '₹' + Number(amount).toLocaleString('en-IN');
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
