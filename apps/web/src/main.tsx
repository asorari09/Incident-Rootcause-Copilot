import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return (
    <main>
      <p className="eyebrow">IR-Copilot</p>
      <h1>Detect with stats. Diagnose with agents.</h1>
      <p>
        The operator dashboard will be connected in Phase 6 after the
        deterministic detector and fixed, draft-only incident workflow exist.
      </p>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
