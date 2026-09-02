import React from "react";
import type { SaveSummaryResponse } from "../../api/schema";

interface ContextRailProps {
  save: SaveSummaryResponse;
}

export function ContextRail({ save }: ContextRailProps): React.JSX.Element {
  return (
    <aside
      aria-label="Adventure Context Rail"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "1.25rem",
        padding: "var(--space-4)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-lg)",
        minWidth: "260px",
      }}
    >
      <div>
        <h3
          style={{
            fontSize: "var(--font-size-xs)",
            color: "var(--color-text-muted)",
            textTransform: "uppercase",
          }}
        >
          Current Location
        </h3>
        <div style={{ fontSize: "var(--font-size-base)", fontWeight: "bold", marginTop: "0.25rem" }}>
          {save.current_area_id}
        </div>
      </div>

      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong style={{ fontSize: "var(--font-size-sm)" }}>{save.player_name}</strong>
          <span
            style={{
              fontSize: "var(--font-size-xs)",
              color: "var(--color-text-muted)",
              textTransform: "capitalize",
            }}
          >
            {save.difficulty}
          </span>
        </div>
        <div
          style={{
            fontSize: "var(--font-size-xs)",
            color: "var(--color-text-muted)",
            marginTop: "0.25rem",
          }}
        >
          {save.slot_name} • Rev {save.revision}
        </div>
      </div>
    </aside>
  );
}
