import React from "react";

interface CombatTurnTrackerProps {
  round: number;
  turnOrder: string[];
  activeEntityId: string;
  isPlayerTurn: boolean;
}

export function CombatTurnTracker({
  round,
  turnOrder,
  activeEntityId,
  isPlayerTurn,
}: CombatTurnTrackerProps): React.JSX.Element {
  return (
    <section
      aria-label="Combat Turn Tracker"
      style={{
        padding: "var(--space-3) var(--space-4)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-lg)",
        marginBottom: "1.5rem",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "1rem",
      }}
    >
      <div>
        <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
          ROUND {round}
        </span>
        <div style={{ fontSize: "var(--font-size-base)", fontWeight: "bold" }}>
          {isPlayerTurn ? (
            <span style={{ color: "var(--color-accent)" }}>★ Your Turn</span>
          ) : (
            <span style={{ color: "var(--color-warning)" }}>Enemy Turn ({activeEntityId})</span>
          )}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>Order:</span>
        <div style={{ display: "flex", gap: "0.25rem" }}>
          {turnOrder.map((entityId, idx) => {
            const isActive = entityId === activeEntityId;
            return (
              <span
                key={idx}
                style={{
                  padding: "2px 6px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--font-size-xs)",
                  backgroundColor: isActive ? "var(--color-accent)" : "var(--color-bg-elevated)",
                  color: isActive ? "var(--color-bg-base)" : "var(--color-text-secondary)",
                  fontWeight: isActive ? "bold" : "normal",
                }}
              >
                {entityId}
              </span>
            );
          })}
        </div>
      </div>
    </section>
  );
}
