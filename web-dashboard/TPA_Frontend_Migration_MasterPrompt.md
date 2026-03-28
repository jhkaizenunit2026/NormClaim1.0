# TPA / Hospital Frontend — Migration Master Prompt
# Version: 2.0 | Architecture: Pre-Auth → Settlement (11-Stage Workflow)
# Use this prompt at the start of every AI-assisted dev session for this project.

---

## SYSTEM CONTEXT — READ FIRST

You are a senior frontend engineer working on a **TPA (Third Party Administrator) and Hospital Claims Management System**. The existing frontend was built on an older, simpler workflow. You are now migrating it to a new **11-stage, role-based, real-time architecture**.

Your job is to **audit, refactor, and extend** existing components — not rewrite everything from scratch unless a module is fundamentally incompatible with the new workflow.

---

## THE NEW WORKFLOW (Source of Truth)

The application must model this exact 11-stage business process. Every UI decision must trace back to one of these stages:

```
Stage 1  → Pre-Authorization Initiation
           Inputs: Pre-Auth Form, ID Proofs, Diagnosis, Referral Letter

Stage 2  → Pre-Auth Approval
           Output: Initial amount approved

Stage 3  → Admission
           Output: Admission Number generated

Stage 4  → Enhancement Request
           Trigger: Additional funds required

Stage 5  → Enhancement Approval
           Output: Additional amount approved

Stage 6  → Discharge Intimation
           Documents: Discharge Summary, Final Bill, ICPs, Internal Case Papers

Stage 7  → Discharge Approval  (~3 hours SLA)
           Outputs: Copay, Deductions, TPA payable amount

Stage 8  → Discharge Completion
           Actions: Patient discharged, hard copy mailed

Stage 9  → Settlement Letter
           Outputs: Further deductions (if any), Final amount, TDS, UTR generated

Stage 10 → Finance Department Processing
           Ledger entries: Account, Date, Amount, UTR, Bill Number

Stage 11 → Closure
           Status: Case closed / settled | Follow-up flagged if needed
```

---

## ROLE-BASED ACCESS MODEL

The frontend must enforce **three distinct user roles**. Each role sees only its own views. Never mix role-specific UI into a shared component without explicit conditional rendering.

| Role | Portal Name | Active Stages | Key Permissions |
|------|-------------|---------------|-----------------|
| `HOSPITAL` | Hospital Portal | All 11 stages (read/submit) | Submit forms, upload docs, track status |
| `TPA` | TPA Dashboard | All 11 stages (review/approve) | Approve/reject, set amounts, issue letters |
| `FINANCE` | Finance Panel | Stages 9–11 only | Ledger entry, UTR tracking, reconciliation |

```js
// Required auth context shape
const user = {
  role: 'HOSPITAL' | 'TPA' | 'FINANCE',
  hospitalId: string | null,
  tpaOfficerId: string | null,
  financeUserId: string | null,
}
```

---

## CLAIM STATE MACHINE (Frontend Enum)

This is the **single source of truth** for UI rendering. Every conditional, every button enable/disable, every route guard must reference this enum. Do not use raw strings.

```ts
// src/constants/claimStatus.ts

export const CLAIM_STATUS = {
  PRE_AUTH_INITIATED:   'PRE_AUTH_INITIATED',   // Stage 1
  PRE_AUTH_APPROVED:    'PRE_AUTH_APPROVED',    // Stage 2
  ADMITTED:             'ADMITTED',             // Stage 3
  ENHANCEMENT_REQUESTED:'ENHANCEMENT_REQUESTED',// Stage 4
  ENHANCEMENT_APPROVED: 'ENHANCEMENT_APPROVED', // Stage 5
  DISCHARGE_INTIMATED:  'DISCHARGE_INTIMATED',  // Stage 6
  DISCHARGE_APPROVED:   'DISCHARGE_APPROVED',   // Stage 7
  DISCHARGE_COMPLETE:   'DISCHARGE_COMPLETE',   // Stage 8
  SETTLEMENT_ISSUED:    'SETTLEMENT_ISSUED',    // Stage 9
  FINANCE_PROCESSED:    'FINANCE_PROCESSED',    // Stage 10
  CLOSED:               'CLOSED',              // Stage 11
} as const;

export type ClaimStatus = typeof CLAIM_STATUS[keyof typeof CLAIM_STATUS];

// Helper: is the current stage at or past a given stage?
export const isAtOrPast = (current: ClaimStatus, target: ClaimStatus): boolean => {
  const order = Object.values(CLAIM_STATUS);
  return order.indexOf(current) >= order.indexOf(target);
};
```

---

## ROUTE MAP

Implement all routes below. Guard each with role checks. Use React Router v6 `<Navigate>` for unauthorized redirects.

```
HOSPITAL PORTAL
/portal/pre-auth/new              → Stage 1: Pre-auth form
/portal/pre-auth/:claimId         → Stage 2: Approval status view
/portal/admission/:claimId        → Stage 3: Admission form + number display
/portal/enhancement/:claimId      → Stage 4: Enhancement request form
/portal/enhancement/:claimId/status → Stage 5: Enhancement approval status
/portal/discharge/:claimId        → Stage 6: Document upload hub
/portal/discharge/:claimId/status → Stage 7: Approval tracker (countdown)
/portal/discharge/:claimId/complete → Stage 8: Discharge confirmation
/portal/settlement/:claimId       → Stage 9: Settlement letter viewer
/portal/payment/:claimId          → Stage 10: Payment status panel
/portal/cases                     → All cases dashboard

TPA DASHBOARD
/tpa/queue                        → Incoming pre-auth queue
/tpa/review/:claimId              → Stage 1+2: Review & decision panel
/tpa/enhancement/:claimId         → Stage 4+5: Enhancement review & approval
/tpa/discharge/:claimId           → Stage 6+7: Document review & discharge approval
/tpa/settlement/:claimId          → Stage 9: Settlement letter generation
/tpa/cases                        → All cases with filters
/tpa/cases/archive                → Closed cases

FINANCE PANEL
/finance/alerts                   → Stage 9: Pending UTR entries
/finance/ledger/entry/:claimId    → Stage 10: Ledger entry form
/finance/settlement/list          → Settlement letter list
/finance/utr/tracker              → UTR tracking dashboard
/finance/tds/report               → TDS report
/finance/reconciliation           → Stage 11: Reconciliation view
```

---

## COMPONENT ARCHITECTURE

### Directory structure to enforce

```
src/
├── components/
│   ├── shared/              ← Used by all roles
│   │   ├── ClaimStatusBadge.tsx
│   │   ├── DocumentUploader.tsx
│   │   ├── NotificationBell.tsx
│   │   ├── AuditTrailTimeline.tsx
│   │   └── StageProgressBar.tsx
│   ├── hospital/            ← HOSPITAL role only
│   │   ├── PreAuthForm.tsx
│   │   ├── AdmissionForm.tsx
│   │   ├── EnhancementRequestForm.tsx
│   │   ├── DischargeDocHub.tsx
│   │   ├── DischargeTracker.tsx
│   │   └── SettlementViewer.tsx
│   ├── tpa/                 ← TPA role only
│   │   ├── PreAuthQueue.tsx
│   │   ├── ReviewDecisionPanel.tsx
│   │   ├── EnhancementApprovalPanel.tsx
│   │   ├── DischargeApprovalPanel.tsx
│   │   └── SettlementLetterGen.tsx
│   └── finance/             ← FINANCE role only
│       ├── LedgerEntryForm.tsx
│       ├── UTRTracker.tsx
│       ├── TDSReport.tsx
│       └── ReconciliationView.tsx
├── pages/
│   ├── portal/              ← Hospital portal pages
│   ├── tpa/                 ← TPA dashboard pages
│   └── finance/             ← Finance panel pages
├── hooks/
│   ├── useClaim.ts          ← Fetch + cache claim by ID
│   ├── useClaimStatus.ts    ← Poll/subscribe to status changes
│   ├── useDocuments.ts      ← Document upload/fetch
│   ├── useNotifications.ts  ← WebSocket notification stream
│   └── useFinanceEntry.ts   ← Ledger entry mutations
├── services/
│   ├── api.ts               ← Axios instance + interceptors
│   ├── socket.ts            ← Socket.io client setup
│   └── auth.ts              ← Token management
├── store/
│   ├── authStore.ts         ← Zustand: user role + session
│   └── notificationStore.ts ← Zustand: unread count + toasts
└── constants/
    └── claimStatus.ts       ← The enum above
```

---

## MIGRATION RULES — WHAT TO DO WITH OLD CODE

Apply these rules file-by-file when touching existing code:

### KEEP (minimal changes)
- Auth/login flows — only add role assignment on login response
- HTTP client setup (Axios base) — add interceptors if missing
- Reusable UI primitives (buttons, inputs, modals) — keep as-is unless styling conflicts
- Utility functions (date formatting, currency formatting) — keep as-is

### REFACTOR (structural changes needed)
- Any component that renders claim data without checking `claimStatus` → add status-gating
- Any route without a role guard → add `<RoleGuard role="HOSPITAL|TPA|FINANCE">` wrapper
- Any form that submits without a document attachment step → wire in `<DocumentUploader>`
- Any status display using raw strings like `"approved"` → replace with `CLAIM_STATUS` enum keys
- Any polling mechanism → migrate to WebSocket subscription (see socket setup below)

### REPLACE (incompatible with new architecture)
- Single-page claim forms that combine pre-auth + admission + discharge → split into per-stage components
- Any flat status field (e.g. `status: "pending" | "done"`) → replace with `ClaimStatus` enum
- Finance entries mixed into the TPA interface → extract to `/finance` panel with `FINANCE` role guard
- Any hardcoded amount fields without copay/deduction breakdown → refactor to settlement breakdown component

### DO NOT TOUCH
- Backend API contracts (coordinate separately)
- Database schema
- Existing test data / seed scripts

---

## API CONTRACT (Frontend Expectations)

Assume the backend exposes these endpoints. If the existing backend differs, note the delta and flag for backend team.

```
GET    /api/claims                          → List claims (filtered by role)
GET    /api/claims/:claimId                 → Single claim with full status
POST   /api/claims                          → Create new pre-auth (Stage 1)
PATCH  /api/claims/:claimId/status          → Advance claim stage
POST   /api/claims/:claimId/enhancement     → Submit enhancement request (Stage 4)
POST   /api/claims/:claimId/discharge       → Submit discharge docs (Stage 6)
GET    /api/claims/:claimId/documents       → List uploaded documents
POST   /api/claims/:claimId/documents       → Upload document (multipart)
POST   /api/claims/:claimId/settlement      → Issue settlement letter (Stage 9)
POST   /api/claims/:claimId/finance-entry   → Record ledger entry (Stage 10)
POST   /api/claims/:claimId/close           → Close case (Stage 11)
GET    /api/notifications                   → Unread notification list
WebSocket: ws://[host]/notifications        → Real-time push channel
```

### Standard claim response shape

```ts
interface Claim {
  claimId: string;
  admissionNumber: string | null;
  patientName: string;
  hospitalId: string;
  tpaOfficerId: string | null;
  status: ClaimStatus;
  preAuthAmount: number | null;
  enhancementAmount: number | null;
  copay: number | null;
  deductions: number | null;
  tpaPayableAmount: number | null;
  finalSettlementAmount: number | null;
  utrNumber: string | null;
  tdsAmount: number | null;
  billNumber: string | null;
  documents: Document[];
  timeline: AuditEntry[];
  createdAt: string;
  updatedAt: string;
  dischargeApprovalDeadline: string | null; // ISO — for the ~3hr countdown
}
```

---

## KEY COMPONENT SPECS

### 1. StageProgressBar (shared)

Renders the 11-stage pipeline. Highlights current stage, grays out future stages, shows checkmarks for completed stages. Used in the page header of every claim detail view.

```tsx
// Props
interface StageProgressBarProps {
  currentStatus: ClaimStatus;
  role: 'HOSPITAL' | 'TPA' | 'FINANCE';
}
// Finance role only renders stages 9–11 in the bar.
// Clicking a completed stage navigates to that stage's detail view.
```

### 2. DocumentUploader (shared)

Handles all document uploads across stages 1, 6. Must support:
- Drag-and-drop + click-to-browse
- File type validation: PDF, JPG, PNG only
- Max size: 10MB per file
- Shows upload progress bar per file
- Lists uploaded documents with preview link + delete option
- Required document checklist per stage (passed as prop)

```tsx
interface DocumentUploaderProps {
  claimId: string;
  stage: 'PRE_AUTH' | 'DISCHARGE';
  requiredDocs: string[]; // e.g. ['Discharge Summary', 'Final Bill', 'ICPs', 'Internal Case Papers']
  onAllUploaded: () => void;
}
```

### 3. DischargeApprovalPanel — TPA (Stage 7)

This is the most complex TPA component. Must show:
- Patient name, admission number, claim ID
- Document list with inline PDF viewer
- Three editable fields: Copay Amount, Deductions (itemized), TPA Payable Amount
- Auto-calculated total check: `preAuthAmount + enhancementAmount - copay - deductions = tpaPayableAmount`
- SLA countdown timer from discharge intimation timestamp (target: ≈3 hours)
- Submit → triggers `PATCH /api/claims/:id/status` with `status: DISCHARGE_APPROVED`
- Real-time save (auto-draft every 30 seconds)

### 4. SettlementLetterGen — TPA (Stage 9)

Generates the settlement letter PDF on the frontend using data from the claim. Must include:
- Claim summary header
- Original approved amount
- Enhancement amount (if any)
- Itemized deductions
- Final payable amount
- TDS amount + UTR number (input field — entered manually by TPA after payment)
- "Generate Letter" button → POST to `/api/claims/:id/settlement`
- "Download PDF" button → renders letter as PDF client-side

### 5. LedgerEntryForm — Finance (Stage 10)

Simple data entry form triggered when UTR is generated. Fields:
- Account Number (dropdown from finance master list)
- Entry Date (date picker, defaults to today)
- Amount (pre-filled from settlement, editable)
- UTR Number (pre-filled from claim, read-only)
- Bill Number (pre-filled from claim, read-only)
- Remarks (text area, optional)
- Submit → POST `/api/claims/:id/finance-entry`

---

## REAL-TIME / WEBSOCKET SETUP

```ts
// src/services/socket.ts
import { io } from 'socket.io-client';

export const socket = io(process.env.REACT_APP_WS_URL!, {
  auth: { token: () => localStorage.getItem('authToken') },
  autoConnect: false,
});

// Events to subscribe to:
// 'claim:status_changed'  → { claimId, newStatus, updatedAt }
// 'claim:document_added'  → { claimId, documentId, documentType }
// 'claim:approval_needed' → { claimId, stage, deadline }
// 'settlement:utr_ready'  → { claimId, utrNumber }
// 'notification:new'      → { id, message, claimId, priority }
```

Every claim detail page must:
1. Connect on mount
2. Join room `claim:{claimId}`
3. On `claim:status_changed` → invalidate React Query cache for that claim
4. On `claim:approval_needed` → show toast + update notification bell count
5. Disconnect on unmount

---

## NOTIFICATION CENTER

- Bell icon in top navbar with unread count badge
- Dropdown shows last 20 notifications
- Each notification links to the relevant claim + stage
- Notifications are role-filtered server-side — hospital users never see TPA internal events
- Mark-all-read button
- Priority levels: `info` | `warning` | `urgent` (urgent = red badge, sound alert optional)

---

## AUDIT TRAIL TIMELINE (shared)

Every claim detail view must include a collapsible audit trail at the bottom. Each entry shows:
- Timestamp
- Actor (user name + role)
- Action taken (e.g. "Pre-auth approved — ₹45,000")
- Stage at time of action

Sourced from `claim.timeline[]` in the claim response.

---

## CODING STANDARDS FOR THIS PROJECT

### State management
- Use **React Query** for all server state (claims, documents, notifications list)
- Use **Zustand** only for: auth session, notification unread count, global toast queue
- No Redux. No Context for server data.

### Forms
- Use **React Hook Form** for all forms
- Validate with **Zod** schemas — define schemas in `src/schemas/`
- Never use uncontrolled inputs for claim data

### Error handling
- Every API call must have an error boundary or explicit error state
- Show user-friendly messages — never expose raw API errors
- Network errors → retry up to 2 times (React Query default), then show "Try again" UI

### Styling
- Use the existing CSS/design system — do not introduce a new styling approach mid-migration
- Stage color coding must be consistent across all components:
  - Teal → Pre-auth + Admission (Stages 1–3)
  - Amber → Enhancement (Stages 4–5)
  - Coral/Orange → Discharge (Stages 6–8)
  - Blue → Settlement + Finance (Stages 9–10)
  - Green → Closed (Stage 11)
  - Gray → TPA internal processing states

### TypeScript
- Strict mode on. No `any` types in claim-related code.
- All API response shapes must have corresponding TypeScript interfaces in `src/types/`

---

## MIGRATION SESSION WORKFLOW

When starting work on any module, follow this sequence:

1. **Identify** — which stage(s) does this module belong to?
2. **Identify role** — which role(s) does this component serve?
3. **Check state machine** — what `claimStatus` values trigger this component to be active?
4. **Audit existing code** — does the old component have incompatible assumptions? List them.
5. **Refactor or replace** — apply the rules from the MIGRATION RULES section above.
6. **Wire real-time** — add WebSocket subscription if this stage involves status changes.
7. **Add route guard** — confirm role guard is in place on the route.
8. **Test state transitions** — manually verify that the component renders correctly for each relevant `claimStatus` value.

---

## WHAT TO ASK THE AI ASSISTANT DURING SESSIONS

Use these prompt patterns for focused, high-quality output:

- "Refactor `[ComponentName].tsx` for Stage [N] of the new workflow. Current code: [paste]. Expected behavior: [describe]."
- "Create the `DischargeApprovalPanel` component for the TPA role per the spec above."
- "Add a route guard to `/tpa/settlement/:claimId` that redirects HOSPITAL and FINANCE roles."
- "Show me the Zod schema for the Pre-Auth form (Stage 1)."
- "Update the claim list page to filter by `claimStatus` using the new enum."
- "Write the `useClaimStatus` hook that subscribes to WebSocket events and invalidates the React Query cache."
- "Generate the `CLAIM_STATUS` enum and `isAtOrPast` helper in TypeScript."
- "What needs to change in `[filename]` to support the Finance role seeing only Stages 9–11?"

---

## QUICK REFERENCE — STAGE TO COMPONENT MAP

| Stage | Hospital Component | TPA Component | Finance Component |
|-------|--------------------|---------------|-------------------|
| 1 | `PreAuthForm` | `PreAuthQueue`, `ReviewDecisionPanel` | — |
| 2 | `ApprovalStatusPanel` | `ReviewDecisionPanel` | — |
| 3 | `AdmissionForm` | `CaseTrackerUpdate` | — |
| 4 | `EnhancementRequestForm` | `EnhancementQueue` | — |
| 5 | `EnhancementStatusPanel` | `EnhancementApprovalPanel` | — |
| 6 | `DischargeDocHub` | `DocumentReviewPanel` | — |
| 7 | `DischargeTracker` | `DischargeApprovalPanel` | — |
| 8 | `DischargeConfirmation` | `DocumentDispatch` | — |
| 9 | `SettlementViewer` | `SettlementLetterGen` | `FinanceAlert` |
| 10 | `PaymentStatusPanel` | `PaymentConfirmation` | `LedgerEntryForm` |
| 11 | `CaseClosedView` | `CaseArchive` | `ReconciliationView` |

---

## KNOWN GAPS IN OLD FRONTEND (Flag for Review)

Check if any of these exist in the old codebase and flag them before migrating:

- [ ] Single combined claim form (pre-auth + admission in one page) → must be split
- [ ] No document upload on pre-auth form → add `DocumentUploader` for Stage 1
- [ ] Status stored as free-text string → migrate to `CLAIM_STATUS` enum
- [ ] Finance entries inside TPA view → extract to Finance Panel
- [ ] No real-time updates (polling only) → migrate to WebSocket
- [ ] No discharge SLA countdown → add timer to Stage 7
- [ ] No UTR field on settlement → add to Stage 9 settlement letter
- [ ] No audit trail / timeline component → add `AuditTrailTimeline`
- [ ] No role-based route guards → add `RoleGuard` to all routes
- [ ] No copay / deductions breakdown in discharge → add itemized fields to Stage 7

---

*End of Master Prompt — paste this at the start of every dev session for this project.*
*Last updated: based on TPA/Hospital Pre-Auth to Settlement workflow v2.0 (11 stages)*
