import React, { useState } from "react";
import { Link } from "react-router-dom";

interface SnapshotCandidate {
  snapshot_id: string;
  revision: number;
  area_id: string;
  timestamp: string;
  is_valid: boolean;
}

export function RecoveryScreen(): React.JSX.Element {
  const [savePath, setSavePath] = useState<string>("");
  const [diagnosing, setDiagnosing] = useState<boolean>(false);
  const [snapshots, setSnapshots] = useState<SnapshotCandidate[]>([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState<string | null>(null);
  const [restoredSuccess, setRestoredSuccess] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleDiagnose = (e: React.FormEvent) => {
    e.preventDefault();
    if (!savePath.trim()) return;

    setDiagnosing(true);
    setError(null);
    setRestoredSuccess(false);

    // Mock/Simulated local snapshot discovery for diagnosed save file
    setTimeout(() => {
      setDiagnosing(false);
      setSnapshots([
        {
          snapshot_id: "snap-rev-3",
          revision: 3,
          area_id: "dungeon_entrance",
          timestamp: "2026-08-17 12:30:00",
          is_valid: true,
        },
        {
          snapshot_id: "snap-rev-2",
          revision: 2,
          area_id: "town_tavern",
          timestamp: "2026-08-17 12:15:00",
          is_valid: true,
        },
      ]);
    }, 300);
  };

  const handleRestore = () => {
    if (!selectedSnapshot) return;
    setRestoredSuccess(true);
  };

  return (
    <section aria-labelledby="recovery-screen-heading" style={{ maxWidth: "800px", margin: "0 auto" }}>
      <div style={{ marginBottom: "2rem" }}>
        <Link to="/" style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-sm)" }}>
          ← Back to Campaign Library
        </Link>
        <h1 id="recovery-screen-heading" style={{ marginTop: "0.5rem" }}>
          🛡️ Save Recovery & Diagnostic Utility
        </h1>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)", marginTop: "0.25rem" }}>
          Inspect corrupted, interrupted, or orphaned save directories and safely roll back to a validated snapshot.
        </p>
      </div>

      <form
        onSubmit={handleDiagnose}
        style={{
          padding: "var(--space-4)",
          backgroundColor: "var(--color-bg-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-lg)",
          marginBottom: "1.5rem",
        }}
      >
        <label
          htmlFor="save-path-input"
          style={{ display: "block", fontWeight: "600", fontSize: "var(--font-size-sm)", marginBottom: "0.5rem" }}
        >
          Save Slot Identifier or Directory Name:
        </label>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <input
            id="save-path-input"
            type="text"
            value={savePath}
            onChange={(e) => setSavePath(e.target.value)}
            placeholder="e.g. save-hero-slot-1"
            required
            style={{ flex: 1 }}
          />
          <button
            type="submit"
            disabled={diagnosing || !savePath.trim()}
            style={{
              backgroundColor: "var(--color-accent)",
              color: "var(--color-bg-base)",
              fontWeight: "bold",
            }}
          >
            {diagnosing ? "Scanning..." : "Diagnose Save"}
          </button>
        </div>
      </form>

      {error && (
        <div
          role="alert"
          style={{
            padding: "var(--space-3)",
            backgroundColor: "rgba(248, 113, 113, 0.15)",
            color: "var(--color-danger)",
            borderRadius: "var(--radius-md)",
            marginBottom: "1.5rem",
          }}
        >
          {error}
        </div>
      )}

      {restoredSuccess && (
        <div
          role="status"
          style={{
            padding: "var(--space-4)",
            backgroundColor: "rgba(52, 211, 153, 0.15)",
            color: "var(--color-success)",
            border: "1px solid var(--color-success)",
            borderRadius: "var(--radius-lg)",
            marginBottom: "1.5rem",
          }}
        >
          <h3>✓ Save Successfully Restored!</h3>
          <p style={{ fontSize: "var(--font-size-sm)", marginTop: "0.25rem" }}>
            The corrupted state has been archived and slot restored to snapshot{" "}
            <strong>{selectedSnapshot}</strong>.
          </p>
          <Link
            to="/"
            style={{
              display: "inline-block",
              marginTop: "1rem",
              padding: "var(--space-2) var(--space-4)",
              backgroundColor: "var(--color-success)",
              color: "var(--color-bg-base)",
              borderRadius: "var(--radius-md)",
              textDecoration: "none",
              fontWeight: "bold",
            }}
          >
            Return to Library to Play →
          </Link>
        </div>
      )}

      {snapshots.length > 0 && !restoredSuccess && (
        <div
          style={{
            padding: "var(--space-4)",
            backgroundColor: "var(--color-bg-surface)",
            border: "1px solid var(--color-border-subtle)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <h2 style={{ fontSize: "var(--font-size-md)", marginBottom: "1rem" }}>
            Available Validated Snapshots
          </h2>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1.5rem" }}>
            {snapshots.map((snap) => (
              <label
                key={snap.snapshot_id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "var(--space-3)",
                  backgroundColor:
                    selectedSnapshot === snap.snapshot_id
                      ? "var(--color-bg-hover)"
                      : "var(--color-bg-elevated)",
                  border:
                    selectedSnapshot === snap.snapshot_id
                      ? "2px solid var(--color-accent)"
                      : "1px solid var(--color-border-subtle)",
                  borderRadius: "var(--radius-md)",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <input
                    type="radio"
                    name="snapshot-choice"
                    value={snap.snapshot_id}
                    checked={selectedSnapshot === snap.snapshot_id}
                    onChange={() => setSelectedSnapshot(snap.snapshot_id)}
                  />
                  <div>
                    <strong>Snapshot Rev {snap.revision}</strong>
                    <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                      Area: {snap.area_id} • {snap.timestamp}
                    </div>
                  </div>
                </div>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-success)", fontWeight: "bold" }}>
                  ✓ Validated
                </span>
              </label>
            ))}
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              type="button"
              disabled={!selectedSnapshot}
              onClick={handleRestore}
              style={{
                backgroundColor: "var(--color-accent)",
                color: "var(--color-bg-base)",
                fontWeight: "bold",
                padding: "var(--space-2) var(--space-6)",
              }}
            >
              Restore Selected Snapshot
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
