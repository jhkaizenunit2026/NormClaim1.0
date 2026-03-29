/**
 * stat-cards-mount.tsx
 * ────────────────────────────────────────────────────────
 * Bridges the vanilla-JS SPA with the React StatCard component.
 *
 * How it works:
 *   1. The vanilla JS components render placeholder <div class="stat-card-react">
 *      elements with data-value and data-label attributes.
 *   2. This script uses a MutationObserver to watch the DOM.
 *      Whenever new placeholders appear (e.g. after a route change)
 *      it mounts a React <StatCard> into each one.
 *   3. Built by Vite into assets/stat-cards.js — loaded as
 *      type="module" in app.html.
 */

import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import StatCard from "../components/ui/stat-card";

// Keep track of already-mounted roots so we don't double-mount
const mountedRoots = new WeakMap<HTMLElement, Root>();

function mountStatCards() {
  const placeholders = document.querySelectorAll<HTMLElement>(
    ".stat-card-react:not([data-mounted])"
  );

  placeholders.forEach((el) => {
    const value = el.dataset.value || "—";
    const label = el.dataset.label || "";

    el.setAttribute("data-mounted", "true");

    const root = createRoot(el);
    mountedRoots.set(el, root);

    root.render(
      <StrictMode>
        <StatCard value={value} label={label} className="w-full h-full" />
      </StrictMode>
    );
  });
}

// Initial scan
mountStatCards();

// Watch for DOM changes (SPA route transitions add new placeholders)
const observer = new MutationObserver(() => {
  mountStatCards();
});

observer.observe(document.body, {
  childList: true,
  subtree: true,
});

// Also expose a global API so vanilla JS can trigger re-render
// after dynamically updating data-value / data-label
(window as any).__updateStatCards = () => {
  // Unmount stale roots whose elements are no longer in the DOM
  document
    .querySelectorAll<HTMLElement>(".stat-card-react[data-mounted]")
    .forEach((el) => {
      if (!document.body.contains(el)) {
        const root = mountedRoots.get(el);
        if (root) {
          root.unmount();
          mountedRoots.delete(el);
        }
      }
    });

  // Re-mount new ones
  mountStatCards();
};

// Also expose a helper to update a single stat card's value
(window as any).__setStatCardValue = (id: string, value: string) => {
  const el = document.getElementById(id);
  if (!el) return;
  el.dataset.value = value;

  // Re-render
  const root = mountedRoots.get(el);
  if (root) {
    root.render(
      <StrictMode>
        <StatCard
          value={value}
          label={el.dataset.label || ""}
          className="w-full h-full"
        />
      </StrictMode>
    );
  }
};
