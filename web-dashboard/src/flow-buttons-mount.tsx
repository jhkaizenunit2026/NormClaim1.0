/**
 * Mounts ShimmerButton-based "Sign In" into the navbar and login page flow points.
 * Built to assets/flow-buttons.js by Vite.
 *
 * The vanilla navbar renders a <span class="nc-flow-mount"> placeholder;
 * this script hydrates each one with a React ShimmerButton.
 */
import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { LogIn, UserPlus } from "lucide-react";
import ShimmerButton from "../components/ui/shimmer-button";

// ── Registry of mounted roots ──────────────────────────
const roots = new Map<Element, Root>();

function openAuth(mode: "signin" | "signup", role?: string | null) {
  (window as any).openAuthDialog?.(mode, role);
}

/** Sweep stale roots whose DOM nodes have been removed. */
function gc() {
  for (const [el, root] of roots) {
    if (!document.body.contains(el)) {
      root.unmount();
      roots.delete(el);
    }
  }
}

/** Mount ShimmerButtons into all unhydrated `.nc-flow-mount` placeholders. */
function hydrate() {
  gc();
  document.querySelectorAll<HTMLElement>(".nc-flow-mount").forEach((el) => {
    if (el.getAttribute("data-nc-flow-mounted") === "true") return;

    const mode =
      el.dataset.flowMode === "signup" ? ("signup" as const) : ("signin" as const);
    const role = el.dataset.flowRole?.trim() || null;
    const label =
      el.dataset.flowLabel ||
      (mode === "signup" ? "Create an account" : "Sign in");
    const isNav = el.classList.contains("nc-flow-mount--nav");

    el.setAttribute("data-nc-flow-mounted", "true");
    const root = createRoot(el);
    roots.set(el, root);
    root.render(
      <StrictMode>
        <ShimmerButton
          type="button"
          className={
            isNav
              ? "!h-9 !px-4 !py-1.5 text-xs font-semibold uppercase tracking-wide"
              : undefined
          }
          onClick={() => openAuth(mode, role)}
        >
          {mode === "signup" ? (
            <UserPlus className="mr-1.5 h-4 w-4 shrink-0" />
          ) : (
            <LogIn className="mr-1.5 h-4 w-4 shrink-0" />
          )}
          {label}
        </ShimmerButton>
      </StrictMode>
    );
  });
}

// Initial pass
hydrate();

// Re-hydrate whenever the DOM mutates (router updates, navbar re-renders).
const observer = new MutationObserver(() => hydrate());
observer.observe(document.body, { childList: true, subtree: true });
