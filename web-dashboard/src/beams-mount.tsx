import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BeamsBackground } from "../components/ui/beams-background";
import "./beams.css";

const rootEl = document.getElementById("beams-root");
if (rootEl) {
  createRoot(rootEl).render(
    <StrictMode>
      <BeamsBackground backgroundOnly intensity="subtle" />
    </StrictMode>
  );
}
