// ═══════════════════════════════════════════════════════════════
// NormClaim — Demo Data (runs when backend is unavailable)
// ═══════════════════════════════════════════════════════════════

const DEMO_CLAIMS = [
  {
    claimId: 'CLM-2024-001', patientName: 'Rajesh Kumar', hospitalId: 'HSP-CITY-01',
    admissionNumber: 'ADM-4521', status: CLAIM_STATUS.PRE_AUTH_INITIATED,
    preAuthAmount: 45000, enhancementAmount: null, copay: null, deductions: null,
    tpaPayableAmount: null, finalSettlementAmount: null, utrNumber: null, tdsAmount: null, billNumber: null,
    diagnosis: 'Community-acquired Pneumonia (J18.9)',
    documents: [], timeline: [], createdAt: '2024-03-12T08:00:00Z', updatedAt: '2024-03-12T08:00:00Z',
    dischargeApprovalDeadline: null,
  },
  {
    claimId: 'CLM-2024-002', patientName: 'Priya Sharma', hospitalId: 'HSP-CITY-01',
    admissionNumber: 'ADM-4522', status: CLAIM_STATUS.ADMITTED,
    preAuthAmount: 65000, enhancementAmount: null, copay: null, deductions: null,
    tpaPayableAmount: null, finalSettlementAmount: null, utrNumber: null, tdsAmount: null, billNumber: null,
    diagnosis: 'Acute Myocardial Infarction (I21.9)',
    documents: [], timeline: [], createdAt: '2024-03-10T10:00:00Z', updatedAt: '2024-03-11T14:00:00Z',
    dischargeApprovalDeadline: null,
  },
  {
    claimId: 'CLM-2024-003', patientName: 'Amit Verma', hospitalId: 'HSP-METRO-02',
    admissionNumber: 'ADM-4523', status: CLAIM_STATUS.DISCHARGE_INTIMATED,
    preAuthAmount: 120000, enhancementAmount: 35000, copay: 8000, deductions: null,
    tpaPayableAmount: null, finalSettlementAmount: null, utrNumber: null, tdsAmount: null, billNumber: 'BILL-2024-789',
    diagnosis: 'Total Knee Replacement (M17.1)',
    documents: [], timeline: [], createdAt: '2024-03-05T09:00:00Z', updatedAt: '2024-03-14T16:00:00Z',
    dischargeApprovalDeadline: new Date(Date.now() + 2 * 3600000).toISOString(),
  },
  {
    claimId: 'CLM-2024-004', patientName: 'Sunita Devi', hospitalId: 'HSP-RURAL-03',
    admissionNumber: 'ADM-4524', status: CLAIM_STATUS.SETTLEMENT_ISSUED,
    preAuthAmount: 30000, enhancementAmount: null, copay: 3000, deductions: 2500,
    tpaPayableAmount: 24500, finalSettlementAmount: 23800, utrNumber: 'UTR20240315001', tdsAmount: 700, billNumber: 'BILL-2024-790',
    diagnosis: 'Cholecystectomy (K80.2)',
    documents: [], timeline: [], createdAt: '2024-03-01T07:00:00Z', updatedAt: '2024-03-15T11:00:00Z',
    dischargeApprovalDeadline: null,
  },
  {
    claimId: 'CLM-2024-005', patientName: 'Mohan Lal', hospitalId: 'HSP-CITY-01',
    admissionNumber: 'ADM-4525', status: CLAIM_STATUS.CLOSED,
    preAuthAmount: 55000, enhancementAmount: 10000, copay: 5000, deductions: 3000,
    tpaPayableAmount: 57000, finalSettlementAmount: 55500, utrNumber: 'UTR20240310002', tdsAmount: 1500, billNumber: 'BILL-2024-788',
    diagnosis: 'Type 2 Diabetes with complications (E11.6)',
    documents: [], timeline: [], createdAt: '2024-02-20T08:00:00Z', updatedAt: '2024-03-10T09:00:00Z',
    dischargeApprovalDeadline: null,
  },
];

const DEMO_TIMELINE = [
  { timestamp: '2024-03-12T08:00:00Z', actor: 'Dr. Mehta (Hospital)', action: 'Pre-auth request submitted — ₹45,000', stage: CLAIM_STATUS.PRE_AUTH_INITIATED },
  { timestamp: '2024-03-12T10:30:00Z', actor: 'Rahul S. (TPA)', action: 'Pre-auth approved — ₹45,000', stage: CLAIM_STATUS.PRE_AUTH_APPROVED },
  { timestamp: '2024-03-12T14:00:00Z', actor: 'System', action: 'Patient admitted — ADM-4521', stage: CLAIM_STATUS.ADMITTED },
  { timestamp: '2024-03-15T09:00:00Z', actor: 'Dr. Mehta (Hospital)', action: 'Discharge documents uploaded', stage: CLAIM_STATUS.DISCHARGE_INTIMATED },
  { timestamp: '2024-03-15T11:30:00Z', actor: 'Rahul S. (TPA)', action: 'Discharge approved — Copay ₹3,000, Deductions ₹2,500', stage: CLAIM_STATUS.DISCHARGE_APPROVED },
];
