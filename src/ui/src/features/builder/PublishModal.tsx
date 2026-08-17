import React, { useState } from "react";

interface PublishModalProps {
  isOpen: boolean;
  publishing: boolean;
  error: string | null;
  onConfirm: () => void;
  onClose: () => void;
}

export function PublishModal({
  isOpen,
  publishing,
  error,
  onConfirm,
  onClose,
}: PublishModalProps): React.JSX.Element | null {
  const [confirmedCheckbox, setConfirmedCheckbox] = useState<boolean>(false);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="publish-dialog-title"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        padding: "1rem",
      }}
    >
      <div
        style={{
          backgroundColor: "var(--color-bg-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-lg)",
          padding: "2rem",
          maxWidth: "540px",
          width: "100%",
        }}
      >
        <h2 id="publish-dialog-title" style={{ marginBottom: "1rem" }}>
          Publish Campaign Pack
        </h2>

        <p style={{ color: "var(--color-text-secondary)", marginBottom: "1rem", lineHeight: "1.4" }}>
          Publishing creates an <strong>immutable, fingerprinted campaign pack</strong>. Once published:
        </p>

        <ul
          style={{
            paddingLeft: "1.5rem",
            color: "var(--color-text-secondary)",
            fontSize: "var(--font-size-sm)",
            marginBottom: "1.5rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
          }}
        >
          <li>The campaign becomes available in the Library to start new games.</li>
          <li>Design files cannot be mutated in-place by save games.</li>
          <li>A canonical SHA-256 content fingerprint will be calculated.</li>
        </ul>

        {error && (
          <div
            role="alert"
            style={{
              padding: "var(--space-3)",
              backgroundColor: "rgba(248, 113, 113, 0.15)",
              color: "var(--color-danger)",
              borderRadius: "var(--radius-md)",
              marginBottom: "1rem",
              fontSize: "var(--font-size-sm)",
            }}
          >
            {error}
          </div>
        )}

        <div style={{ marginBottom: "1.5rem" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={confirmedCheckbox}
              onChange={(e) => setConfirmedCheckbox(e.target.checked)}
              style={{ width: "auto" }}
            />
            <span style={{ fontSize: "var(--font-size-sm)", fontWeight: "600" }}>
              I confirm I want to publish this immutable campaign pack.
            </span>
          </label>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem" }}>
          <button
            type="button"
            onClick={onClose}
            style={{ backgroundColor: "transparent", color: "var(--color-text-secondary)" }}
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!confirmedCheckbox || publishing}
            onClick={onConfirm}
            style={{
              backgroundColor: "var(--color-success)",
              color: "var(--color-bg-base)",
              fontWeight: "bold",
            }}
          >
            {publishing ? "Publishing..." : "Confirm & Publish"}
          </button>
        </div>
      </div>
    </div>
  );
}
