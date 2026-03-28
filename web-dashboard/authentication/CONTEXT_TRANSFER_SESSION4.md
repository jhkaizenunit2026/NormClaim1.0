# NORMCLAIM — FULL PROJECT CONTEXT TRANSFER
# Paste this at the START of every new chat session.
# The AI must read the entire file before responding to anything.
# Last updated: Session 4 — Auth system complete.

---

## PROJECT IDENTITY

**Project name:** Normclaim
**What it is:** A TPA (Third Party Administrator) + Hospital Claims Management System.
**Frontend folder:** `web-dashboard/` (Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui)
**Backend:** Exists separately — DO NOT touch it unless I explicitly ask. Never modify backend files.
**Rule:** Only work inside `web-dashboard/` unless I say otherwise.

---

## TECH STACK (decided — not up for debate)

| Concern | Library |
|---------|---------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript (strict) |
| Styling | Tailwind CSS + shadcn/ui |
| Auth | Supabase Auth (email + Google + GitHub OAuth) |
| Server state | React Query (TanStack Query v5) |
| Local/UI state | Zustand (with persist middleware) |
| Forms | React Hook Form + Zod |
| Real-time | Socket.io client |
| Icons | lucide-react |
| DB client | Supabase JS client (`@supabase/supabase-js`) |

---

## THE 11-STAGE BUSINESS WORKFLOW (source of truth — never change this)

```
Stage 1  → PRE_AUTH_INITIATED    Hospital submits pre-auth form + ID + diagnosis + referral
Stage 2  → PRE_AUTH_APPROVED     TPA approves initial amount
Stage 3  → ADMITTED              Patient admitted, admission number generated
Stage 4  → ENHANCEMENT_REQUESTED Hospital requests additional funds
Stage 5  → ENHANCEMENT_APPROVED  TPA approves additional amount
Stage 6  → DISCHARGE_INTIMATED   Hospital uploads: discharge summary, final bill, ICPs, case papers
Stage 7  → DISCHARGE_APPROVED    TPA sets copay, deductions, TPA payable (~3hr SLA)
Stage 8  → DISCHARGE_COMPLETE    Patient discharged, hard copy mailed
Stage 9  → SETTLEMENT_ISSUED     TPA issues settlement letter + UTR generated
Stage 10 → FINANCE_PROCESSED     Finance records ledger entry (account, date, amount, UTR, bill no.)
Stage 11 → CLOSED                Case closed, follow-up flagged if needed
```

---

## THREE USER ROLES

| Role | Portal | Route prefix | Active stages |
|------|--------|--------------|---------------|
| `HOSPITAL` | Hospital Portal | `/portal/...` | All 11 |
| `TPA` | TPA Dashboard | `/tpa/...` | All 11 |
| `FINANCE` | Finance Panel | `/finance/...` | 9–11 only |

---

## CURRENT PROJECT STATUS

### What has been COMPLETED (do not redo):

#### Session 1–2: Architecture + planning
- Full 11-stage frontend architecture diagram
- Route map for all three portals
- Component directory structure defined
- Migration master prompt written
- Context transfer prompt v1 written

#### Session 3: Auth system — ALL FILES CREATED

**`src/lib/supabase.ts`** — Supabase client init from env vars

**`src/types/auth.ts`** — TypeScript types:
- `UserRole = "HOSPITAL" | "TPA" | "FINANCE"`
- `AuthUser { id, email, name, role, hospitalId?, tpaOfficerId?, financeUserId?, avatarUrl? }`
- `AuthMode = "login" | "signup" | "forgot"`
- `AuthDialogState { isOpen, mode }`

**`src/store/authStore.ts`** — Zustand store (persisted):
- State: `user`, `isLoading`, `dialog`
- Actions: `openAuthDialog(mode?)`, `closeAuthDialog()`, `setDialogMode(mode)`
- Auth: `login(email, pw)`, `signup(email, pw, name, role)`, `loginWithProvider(provider)`, `logout()`, `setUser(user)`
- On login/signup: fetches profile from `profiles` table, maps to `AuthUser`

**`src/hooks/useAuthDialog.ts`** — `requireAuth(action?, mode?)` — if logged in runs action, else opens dialog

**`src/components/auth/AuthDialog.tsx`** — The main auth dialog:
- Split panel: left = Normclaim branding, right = form
- Tabs: login / signup / forgot password
- Google OAuth + GitHub OAuth buttons (via Supabase)
- Email + password with show/hide
- Signup: name field + role selector (Hospital / TPA / Finance) as 3-button grid
- Forgot: sends Supabase password reset email
- Error display, loading spinners, Escape-to-close, focus on open
- Orange (`orange-500`) brand color throughout

**`src/components/auth/AuthButton.tsx`** — Drop-in button:
- `<AuthButton mode="signup">` → opens dialog
- `<AuthButton protectedAction={() => fn()}>` → runs fn if logged in, opens dialog if not
- Variants: `default` (orange), `ghost`, `outline`

**`src/components/auth/UserMenu.tsx`** — Shows when logged in:
- Avatar with initials or avatarUrl
- Role badge (color-coded by role)
- Dropdown: Profile, Settings, Sign out
- Shows Sign in / Get started buttons when logged out

**`src/components/auth/RoleGuard.tsx`** — Route protection:
- `<RoleGuard allow="TPA">` or `<RoleGuard allow={["HOSPITAL","TPA"]}>`
- Opens auth dialog if not logged in
- Shows 403 if wrong role
- Loading spinner while resolving

**`src/components/auth/index.ts`** — Barrel export for auth components

**`src/app/auth/callback/route.ts`** — Supabase OAuth redirect handler (exchanges code for session)

**`src/hooks/useSupabaseSession.ts`** — Syncs Supabase session → Zustand on page load + auth state changes

**`src/components/Providers.tsx`** — Client wrapper that calls `useSupabaseSession()`, mounted at root

**`src/app/layout.tsx`** — Root layout with `<Providers>` + `<AuthDialog>` mounted globally

#### Session 4: Foundation layer — COMPLETED

**`src/constants/claimStatus.ts`** — THE enum:
```ts
CLAIM_STATUS = { PRE_AUTH_INITIATED, PRE_AUTH_APPROVED, ADMITTED, ENHANCEMENT_REQUESTED,
  ENHANCEMENT_APPROVED, DISCHARGE_INTIMATED, DISCHARGE_APPROVED, DISCHARGE_COMPLETE,
  SETTLEMENT_ISSUED, FINANCE_PROCESSED, CLOSED }
```
Plus helpers: `isAtOrPast()`, `isBefore()`, `stageNumber()`, `nextStatus()`
Plus maps: `CLAIM_STATUS_LABEL`, `CLAIM_STATUS_COLOR` (Tailwind classes)

**`src/components/shared/StageProgressBar.tsx`**
- Renders all 11 stages as numbered dots with connector lines
- Finance role: shows only stages 9–11
- Completed stages: checkmark + colored dot; current: orange ring + scale-up; future: gray
- Clickable completed stages (calls `onStageClick`)

**`src/components/shared/ClaimStatusBadge.tsx`**
- Small pill badge for any claim status
- Uses `CLAIM_STATUS_COLOR` for automatic color by stage group

**`src/components/shared/AuditTrailTimeline.tsx`**
- Vertical timeline of `AuditEntry[]`
- Shows: stage label, action description, actor name + role (color-coded), timestamp
- Indian date format via `Intl.DateTimeFormat`

**`src/components/shared/NotificationBell.tsx`**
- Bell icon with red unread count badge
- Hover dropdown with last 15 notifications
- Priority colors: urgent=red, warning=amber, info=blue
- Unauthenticated: clicking opens login dialog
- Uses separate `useNotificationStore` (Zustand, not persisted)

**`src/components/shared/index.ts`** — Barrel export

**`src/components/layout/DashboardNav.tsx`**
- Sticky header with Normclaim logo
- Role-based nav links (different links per HOSPITAL/TPA/FINANCE)
- NotificationBell + UserMenu on the right

**`src/app/page.tsx`** — Home/landing page
- Hero with `<AuthButton>` CTAs (opens dialog on click)
- Three feature cards (Hospital/TPA/Finance) each with an `<AuthButton>`

**`src/components/ui/full-screen-signup.tsx`** — Full-page signup form
- Per the HextaStudio component spec provided
- Wired to `useAuthStore().signup()` instead of console.log
- Normclaim branding + stage callouts on left panel

**`supabase/migrations/001_create_profiles.sql`**
- `profiles` table: id (FK auth.users), email, name, role, hospital_id, tpa_officer_id, finance_user_id, avatar_url
- RLS: own read, own update, service role full access
- Trigger: auto-creates profile row on `auth.users` insert
- Trigger: auto-updates `updated_at`
- Indexes on role, hospital_id, tpa_officer_id

**`.env.example`** — Required env vars:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NEXT_PUBLIC_APP_URL`
- `NEXT_PUBLIC_WS_URL`

---

## FULL FILE TREE (current state)

```
web-dashboard/
├── .env.example
├── supabase/
│   └── migrations/
│       └── 001_create_profiles.sql
└── src/
    ├── app/
    │   ├── layout.tsx                        ✅ Done
    │   ├── page.tsx                          ✅ Done
    │   └── auth/
    │       └── callback/
    │           └── route.ts                  ✅ Done
    ├── components/
    │   ├── Providers.tsx                     ✅ Done
    │   ├── auth/
    │   │   ├── index.ts                      ✅ Done
    │   │   ├── AuthDialog.tsx                ✅ Done
    │   │   ├── AuthButton.tsx                ✅ Done
    │   │   ├── UserMenu.tsx                  ✅ Done
    │   │   └── RoleGuard.tsx                 ✅ Done
    │   ├── shared/
    │   │   ├── index.ts                      ✅ Done
    │   │   ├── StageProgressBar.tsx          ✅ Done
    │   │   ├── ClaimStatusBadge.tsx          ✅ Done
    │   │   ├── AuditTrailTimeline.tsx        ✅ Done
    │   │   └── NotificationBell.tsx          ✅ Done
    │   ├── layout/
    │   │   └── DashboardNav.tsx              ✅ Done
    │   └── ui/
    │       └── full-screen-signup.tsx        ✅ Done
    ├── constants/
    │   └── claimStatus.ts                    ✅ Done
    ├── hooks/
    │   ├── useAuthDialog.ts                  ✅ Done
    │   └── useSupabaseSession.ts             ✅ Done
    ├── lib/
    │   └── supabase.ts                       ✅ Done
    ├── store/
    │   └── authStore.ts                      ✅ Done
    └── types/
        └── auth.ts                           ✅ Done

    ─── NOT YET BUILT ───────────────────────
    ├── components/
    │   ├── hospital/                         ⬜ TODO
    │   │   ├── PreAuthForm.tsx
    │   │   ├── AdmissionForm.tsx
    │   │   ├── EnhancementRequestForm.tsx
    │   │   ├── DischargeDocHub.tsx
    │   │   ├── DischargeTracker.tsx
    │   │   └── SettlementViewer.tsx
    │   ├── tpa/                              ⬜ TODO
    │   │   ├── PreAuthQueue.tsx
    │   │   ├── ReviewDecisionPanel.tsx
    │   │   ├── EnhancementApprovalPanel.tsx
    │   │   ├── DischargeApprovalPanel.tsx    ← most complex
    │   │   └── SettlementLetterGen.tsx
    │   └── finance/                          ⬜ TODO
    │       ├── LedgerEntryForm.tsx
    │       ├── UTRTracker.tsx
    │       ├── TDSReport.tsx
    │       └── ReconciliationView.tsx
    ├── hooks/
    │   ├── useClaim.ts                       ⬜ TODO
    │   ├── useClaimStatus.ts                 ⬜ TODO
    │   ├── useDocuments.ts                   ⬜ TODO
    │   └── useFinanceEntry.ts                ⬜ TODO
    ├── services/
    │   ├── api.ts                            ⬜ TODO
    │   └── socket.ts                         ⬜ TODO
    └── app/
        ├── portal/                           ⬜ TODO (Hospital pages)
        ├── tpa/                              ⬜ TODO (TPA pages)
        └── finance/                          ⬜ TODO (Finance pages)
```

---

## NEXT TASKS (in order — do the top one first)

```
[ ] 1. services/api.ts          — Axios instance + auth interceptors
[ ] 2. services/socket.ts       — Socket.io client, event types
[ ] 3. hooks/useClaim.ts        — React Query: fetch single claim by ID
[ ] 4. hooks/useClaimStatus.ts  — Subscribe to WebSocket status changes + invalidate cache
[ ] 5. hooks/useDocuments.ts    — Upload + fetch documents for a claim
[ ] 6. DocumentUploader shared component
[ ] 7. Hospital Portal pages (portal/)
[ ] 8. TPA Dashboard pages (tpa/)
[ ] 9. Finance Panel pages (finance/)
[ ] 10. Real-time WebSocket wiring across all components
[ ] 11. E2E test: full claim run Stage 1 → Stage 11
```

---

## KEY PATTERNS TO FOLLOW IN EVERY FILE

### 1. No raw status strings — always use the enum
```ts
// WRONG
if (claim.status === "admitted") { ... }

// RIGHT
import { CLAIM_STATUS, isAtOrPast } from "@/constants/claimStatus";
if (isAtOrPast(claim.status, CLAIM_STATUS.ADMITTED)) { ... }
```

### 2. Protect every route with RoleGuard
```tsx
// In any page component
<RoleGuard allow="TPA">
  <DischargeApprovalPanel claimId={claimId} />
</RoleGuard>
```

### 3. Every button that needs auth uses AuthButton or useAuthDialog
```tsx
// Option A — simple
<AuthButton mode="login">Sign in to continue</AuthButton>

// Option B — protect an existing action
const { requireAuth } = useAuthDialog();
<button onClick={() => requireAuth(() => submitClaim())}>
  Submit pre-auth
</button>
```

### 4. Forms: React Hook Form + Zod
```ts
const schema = z.object({ email: z.string().email(), ... });
const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) });
```

### 5. Server state: React Query
```ts
const { data: claim, isLoading } = useQuery({
  queryKey: ["claim", claimId],
  queryFn: () => api.get(`/claims/${claimId}`).then(r => r.data),
});
```

### 6. Colors are fixed — use these Tailwind classes
| Stage group | Color |
|-------------|-------|
| Pre-auth + Admission (1–3) | `teal` |
| Enhancement (4–5) | `amber` |
| Discharge (6–8) | `orange` |
| Settlement + Finance (9–10) | `blue` |
| Closed (11) | `green` |
| TPA internal | `zinc/gray` |
| Brand / CTA | `orange-500` |

---

## SUPABASE SETUP CHECKLIST (for when you configure the project)

```
[ ] Create project at https://app.supabase.com
[ ] Copy URL + anon key → .env.local
[ ] Run supabase/migrations/001_create_profiles.sql in SQL Editor
[ ] Enable Google OAuth: Auth → Providers → Google (add Client ID + Secret)
[ ] Enable GitHub OAuth: Auth → Providers → GitHub (add Client ID + Secret)
[ ] Set redirect URLs: Auth → URL Configuration → Add http://localhost:3000/auth/callback
[ ] Install deps: npm install @supabase/supabase-js @supabase/auth-helpers-nextjs
```

---

## INSTALL COMMAND (run once in web-dashboard/)

```bash
npm install \
  @supabase/supabase-js \
  @supabase/auth-helpers-nextjs \
  zustand \
  @tanstack/react-query \
  react-hook-form \
  @hookform/resolvers \
  zod \
  axios \
  socket.io-client \
  lucide-react \
  @radix-ui/react-dialog \
  @radix-ui/react-dropdown-menu
```

---

## HOW TO INTERACT WITH ME IN NEW SESSIONS

After pasting this prompt, confirm you understand by saying:
> "Context loaded. Normclaim web-dashboard — auth + foundation complete.
>  Next task: [top item from TODO list]. Ready."

Then wait for my instruction. Do not start coding until I give the go-ahead.

When I share code snippets or existing files:
- Map them to the correct stage(s) and role(s)
- Check against this context before suggesting anything
- Flag conflicts with decided architecture before proceeding

When building new components:
- Use the file paths from the tree above exactly
- Use the enum, not raw strings
- Add RoleGuard to every page
- TypeScript strict — no `any`
- Always export from a barrel `index.ts` if the folder has 2+ files

---

*End of context transfer. Session 4 complete — auth system + foundation layer done.*
*Next session starts at: services/api.ts (Axios instance)*
