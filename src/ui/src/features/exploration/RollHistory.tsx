import React from "react";

export interface RollHistoryItem {
  id: string;
  checkId: string;
  trait: string;
  dc: number;
  total?: number;
  outcome: string;
  timestamp: string;
}

interface RollHistoryProps {
  history: RollHistoryItem[];
}

export function RollHistory({ history }: RollHistoryProps): React.JSX.Element {
  if (history.length === 0) {
    return (
      <section
        aria-label="Roll History"
        style={{
          padding: "var(--space-3)",
          backgroundColor: "var(--color-bg-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-md)",
          fontSize: "var(--font-size-xs)",
          color: "var(--color-text-muted)",
        }}
      >
        No dice rolls recorded yet.
      </section>
    );
  }

  return (
    <section
      aria-label="Roll History"
      style={{
        padding: "var(--space-3)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <h3 style={{ fontSize: "var(--font-size-xs)", textTransform: "uppercase", marginBottom: "0.5rem", color: "var(--color-text-muted)" }}>
        Recent Rolls
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {history.map((h) => (
          <div
            key={h.id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "var(--font-size-xs)",
              padding: "4px 8px",
              backgroundColor: "var(--color-bg-elevated)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            <div>
              <strong style={{ textTransform: "capitalize" }}>{h.trait}</strong> (DC {h.dc})
            </div>
            <div style={{ color: "var(--color-accent)", fontWeight: "bold" }}>
              {h.outcome}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
