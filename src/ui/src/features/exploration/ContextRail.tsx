import React from "react";
import type { RuntimeStateResponse } from "../../api/schema";

interface ContextRailProps {
  runtimeState: RuntimeStateResponse;
}

export function ContextRail({ runtimeState }: ContextRailProps): React.JSX.Element {
  const { player, current_area_id } = runtimeState;

  const hpPercent = Math.round((player.hp / player.max_hp) * 100);
  const manaPercent = Math.round((player.mana / player.max_mana) * 100);

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
      {/* Current Area */}
      <div>
        <h3 style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
          Current Location
        </h3>
        <div style={{ fontSize: "var(--font-size-base)", fontWeight: "bold", marginTop: "0.25rem" }}>
          {current_area_id}
        </div>
      </div>

      {/* Hero Stats */}
      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "0.5rem",
          }}
        >
          <strong style={{ fontSize: "var(--font-size-sm)" }}>{player.name}</strong>
          <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
            Lvl {player.level}
          </span>
        </div>

        {/* HP Bar */}
        <div style={{ marginBottom: "0.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--font-size-xs)", marginBottom: "2px" }}>
            <span>HP</span>
            <span>
              {player.hp} / {player.max_hp}
            </span>
          </div>
          <div
            style={{
              height: "8px",
              backgroundColor: "var(--color-bg-base)",
              borderRadius: "4px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${hpPercent}%`,
                height: "100%",
                backgroundColor: hpPercent > 30 ? "var(--color-success)" : "var(--color-danger)",
              }}
            />
          </div>
        </div>

        {/* Mana Bar */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--font-size-xs)", marginBottom: "2px" }}>
            <span>Mana</span>
            <span>
              {player.mana} / {player.max_mana}
            </span>
          </div>
          <div
            style={{
              height: "8px",
              backgroundColor: "var(--color-bg-base)",
              borderRadius: "4px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${manaPercent}%`,
                height: "100%",
                backgroundColor: "var(--color-accent)",
              }}
            />
          </div>
        </div>
      </div>

      {/* Attributes */}
      <div>
        <h3 style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase", marginBottom: "0.5rem" }}>
          Attributes
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "var(--font-size-xs)" }}>
          {Object.entries(player.attributes).map(([attr, val]) => (
            <div
              key={attr}
              style={{
                padding: "4px 8px",
                backgroundColor: "var(--color-bg-elevated)",
                borderRadius: "var(--radius-sm)",
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <span style={{ textTransform: "capitalize" }}>{attr}</span>
              <strong>{val}</strong>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
