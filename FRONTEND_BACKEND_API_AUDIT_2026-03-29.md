# Frontend-Backend API Connectivity Audit

Date: 2026-03-29  
Scope: web-dashboard (active JS app) <-> backend (FastAPI)

## Executive Summary

Backend is reachable and healthy on port 8000, and most claim/document/analytics endpoints exist and are wired.  
However, the active frontend auth flow generates local mock tokens that cannot authenticate against backend Supabase JWT validation, so protected API calls fail with 401 in real usage.

Overall status: Partially connected, functionally blocked by auth mismatch.

## What Was Checked

1. Frontend API client paths and auth header behavior.
2. Backend router registration and OpenAPI path inventory.
3. Live API probes against running backend.
4. Route parity between frontend calls and backend paths.

## Live Connectivity Results

1. GET /health -> 200 OK
2. GET /api/config/public -> 200 OK
3. GET /api/claims (no auth) -> 401 Missing Authorization header
4. GET /api/claims (Authorization: Bearer local_demo_token) -> 401 invalid JWT
5. GET /api/documents (Authorization: Bearer local_demo_token) -> 401 invalid JWT
6. GET /api/analytics (Authorization: Bearer local_demo_token) -> 401 invalid JWT
7. GET /api/notifications (Authorization: Bearer local_demo_token) -> 404 Not Found
8. GET /openapi.json -> 200, 25 backend paths published

## Endpoint Parity Matrix (Frontend -> Backend)

1. /api/config/public: Present, reachable.
2. /api/claims: Present.
3. /api/claims/{claimId}: Present.
4. /api/claims/{claimId}/status: Present.
5. /api/claims/{claimId}/enhancement: Present.
6. /api/claims/{claimId}/discharge: Present.
7. /api/claims/{claimId}/documents: Present.
8. /api/documents: Present.
9. /api/claims/{claimId}/settlement: Present.
10. /api/claims/{claimId}/finance-entry: Present.
11. /api/claims/{claimId}/close: Present.
12. /api/analytics: Present.
13. /api/notifications: Missing (frontend calls it, backend has no route).

## Findings (Ordered by Severity)

## 1. Critical: Frontend token model is incompatible with backend auth validation

Frontend uses local-storage mock sessions/tokens (token format like local_xxx), while backend requires valid Supabase JWT bearer tokens for protected routes.

Evidence:
- Frontend local auth generates token strings in [web-dashboard/js/local-db.js](web-dashboard/js/local-db.js#L95)
- Frontend auth store uses local token for API calls in [web-dashboard/js/auth.js](web-dashboard/js/auth.js#L44)
- Backend token validation requires Supabase-authenticated JWT in [backend/services/auth.py](backend/services/auth.py#L17)
- Live probe with local token returns 401 invalid JWT

Impact:
- Most frontend API calls fail in non-demo mode.
- Dashboard silently falls back to demo data in many places, masking integration failure.

## 2. High: Missing backend endpoint for frontend notifications call

Frontend calls /api/notifications, but backend does not expose this route.

Evidence:
- Frontend call in [web-dashboard/js/api.js](web-dashboard/js/api.js#L108)
- No notifications route in backend routers (and /openapi.json path list)
- Live probe returns 404

Impact:
- Notification bell/related UX will fail when endpoint is invoked.

## 3. High: Port mismatch risk during manual run

Frontend API base is hardcoded to port 8000, but current terminal context showed backend attempted on port 8001 earlier.

Evidence:
- Frontend base URL in [web-dashboard/js/api.js](web-dashboard/js/api.js#L7)
- Frontend base URL in [web-dashboard/js/supabase-client.js](web-dashboard/js/supabase-client.js#L8)
- User terminal context: uvicorn started on 8001 previously

Impact:
- If backend runs on 8001 while frontend targets 8000, all calls fail with network errors.

## 4. Medium: Upload file-type contract mismatch (UI accepts images, backend accepts only PDF)

Frontend uploader allows .jpg/.jpeg/.png, while backend upload endpoint enforces application/pdf and %PDF magic bytes.

Evidence:
- Frontend accept filter in [web-dashboard/js/components/shared.js](web-dashboard/js/components/shared.js#L141)
- Frontend extension check in [web-dashboard/js/components/shared.js](web-dashboard/js/components/shared.js#L152)
- Backend PDF-only check in [backend/routers/documents.py](backend/routers/documents.py#L52)

Impact:
- User can select image files in UI, then upload fails with 415.

## 5. Medium: claimId is passed by frontend upload flow but not used by backend upload API

Frontend uploader passes claimId into Api.uploadDocument, but backend /api/documents endpoint does not take claimId and stores a document without explicit claim linkage in this route.

Evidence:
- Upload caller with claimId in [web-dashboard/js/components/shared.js](web-dashboard/js/components/shared.js#L163)
- Api method signature includes claimId argument in [web-dashboard/js/api.js](web-dashboard/js/api.js#L78)
- Backend upload signature in [backend/routers/documents.py](backend/routers/documents.py#L35)

Impact:
- Claim-document association may be incomplete/indirect for claim-level document retrieval UX.

## 6. Low: Startup warning indicates schema drift in Supabase table

Backend startup logs warn that fhir_bundles.created_at column does not exist during cache bootstrap.

Evidence:
- Runtime startup warning observed while launching uvicorn

Impact:
- Cache bootstrap partially degraded; potential stale or incomplete in-memory preload.

## APIs Not Used by Active Frontend (Observation)

These backend APIs are available but not called by the active web-dashboard JS app:

1. /api/extract/{document_id}
2. /api/fhir/{document_id}
3. /api/reconcile/{document_id}
4. /api/review/{document_id}
5. /api/feedback/{document_id}
6. /api/validate/{document_id}
7. /api/auth/session
8. /api/preauth/*

Note: Some are used by old-webfrontend pages, not by the current component-driven app.

## Recommended Fix Plan

## Phase 1 (Immediate)

1. Unify auth: replace LocalDB-only login flow with Supabase sign-in and real access token propagation.
2. Add or remove /api/notifications contract:
   - Add backend route if feature is needed, or
   - Remove frontend call if not used.
3. Keep frontend and backend on same port contract (default backend 8000), or make API base configurable via environment/runtime config.

## Phase 2 (Short Term)

1. Align upload contract:
   - Either restrict frontend uploader to PDF only, or
   - Extend backend to support image uploads.
2. Add explicit claimId association in document upload API (field or separate endpoint).

## Phase 3 (Stability)

1. Resolve fhir_bundles schema drift (add missing created_at or adjust query model).
2. Add integration smoke tests for:
   - auth/session
   - claims list
   - claim update lifecycle
   - document upload
   - analytics

## Conclusion

The transport layer and most route mappings are in place, but production-like frontend usage is blocked by authentication incompatibility and one missing endpoint. Once auth is unified and minor contract mismatches are fixed, frontend-backend integration should be stable.
