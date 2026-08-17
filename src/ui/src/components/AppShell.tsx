import React, { type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

interface AppShellProps {
  children?: ReactNode;
  activeCampaignId?: string | null;
  activeSaveId?: string | null;
  activeRevision?: number | null;
}

export function AppShell({
  children,
  activeCampaignId,
  activeSaveId,
  activeRevision,
}: AppShellProps): React.JSX.Element {
  const location = useLocation();

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "var(--space-4) var(--space-6)",
          backgroundColor: "var(--color-bg-surface)",
          borderBottom: "1px solid var(--color-border-subtle)",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
          <Link
            to="/"
            style={{
              fontSize: "var(--font-size-xl)",
              fontWeight: "bold",
              color: "var(--color-text-primary)",
              textDecoration: "none",
              letterSpacing: "0.05em",
            }}
          >
            STORYMODE
          </Link>

          <nav aria-label="Main Navigation" style={{ display: "flex", gap: "1rem" }}>
            <Link
              to="/"
              style={{
                color: location.pathname === "/" ? "var(--color-accent)" : "var(--color-text-secondary)",
                textDecoration: "none",
                fontSize: "var(--font-size-sm)",
                fontWeight: location.pathname === "/" ? "600" : "400",
              }}
            >
              Library
            </Link>
            <Link
              to="/builder/guided"
              style={{
                color: location.pathname.startsWith("/builder")
                  ? "var(--color-accent)"
                  : "var(--color-text-secondary)",
                textDecoration: "none",
                fontSize: "var(--font-size-sm)",
                fontWeight: location.pathname.startsWith("/builder") ? "600" : "400",
              }}
            >
              Builder
            </Link>
            <Link
              to="/recovery"
              style={{
                color: location.pathname === "/recovery"
                  ? "var(--color-accent)"
                  : "var(--color-text-secondary)",
                textDecoration: "none",
                fontSize: "var(--font-size-sm)",
                fontWeight: location.pathname === "/recovery" ? "600" : "400",
              }}
            >
              Recovery
            </Link>
          </nav>
        </div>

        {/* Status slot for active campaign / save */}
        <div
          aria-label="Active Game Status"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            fontSize: "var(--font-size-xs)",
            color: "var(--color-text-muted)",
          }}
        >
          {activeCampaignId ? (
            <span>
              Campaign: <strong style={{ color: "var(--color-text-primary)" }}>{activeCampaignId}</strong>
            </span>
          ) : (
            <span>No Active Campaign</span>
          )}
          {activeSaveId && (
            <span>
              Save: <strong style={{ color: "var(--color-text-primary)" }}>{activeSaveId}</strong>
            </span>
          )}
          {activeRevision !== null && activeRevision !== undefined && (
            <span>
              Rev: <strong style={{ color: "var(--color-text-primary)" }}>{activeRevision}</strong>
            </span>
          )}
        </div>
      </header>

      <main
        id="main-content"
        tabIndex={-1}
        style={{
          flex: 1,
          padding: "var(--space-6)",
          maxWidth: "1400px",
          width: "100%",
          margin: "0 auto",
        }}
      >
        {children}
      </main>

      <footer
        style={{
          padding: "var(--space-4) var(--space-6)",
          borderTop: "1px solid var(--color-border-subtle)",
          textAlign: "center",
          fontSize: "var(--font-size-xs)",
          color: "var(--color-text-muted)",
        }}
      >
        Storymode — Local-First Single-Player RPG Engine
      </footer>
    </div>
  );
}
