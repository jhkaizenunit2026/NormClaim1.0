/**
 * Full-screen auth overlay — built to assets/auth-overlay.js
 * Vanilla app opens via: openAuthDialog('signin'|'signup', 'HOSPITAL'|...)
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AuthOverlayRoot } from "../auth/components/auth-overlay-root";
import "./auth.css";

const el = document.getElementById("auth-root");
if (el) {
  createRoot(el).render(
    <StrictMode>
      <AuthOverlayRoot />
    </StrictMode>
  );
}
