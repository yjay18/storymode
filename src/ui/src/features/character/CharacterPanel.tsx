import React from "react";
import type { RuntimeStateResponse } from "../../api/schema";

interface CharacterPanelProps {
  runtimeState: RuntimeStateResponse;
}

export function CharacterPanel({ runtimeState }: CharacterPanelProps): React.JSX.Element {
  const { player } = runtimeState;

  return (
    <section
      aria-label="Character Sheet"
      style={{
        padding: "var(--space-4)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "var(--font-size-xl)" }}>{player.name}</h2>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
          Level {player.level} Hero
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>Hit Points</span>
          <div style={{ fontSize: "var(--font-size-lg)", fontWeight: "bold", color: "var(--color-success)" }}>
            {player.hp} / {player.max_hp}
          </div>
        </div>
        <div>
          <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>Mana Pool</span>
          <div style={{ fontSize: "var(--font-size-lg)", fontWeight: "bold", color: "var(--color-accent)" }}>
            {player.mana} / {player.max_mana}
          </div>
        </div>
      </div>

      <div style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "var(--font-size-sm)", textTransform: "uppercase", color: "var(--color-text-muted)", marginBottom: "0.75rem" }}>
          Core Attributes
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", gap: "0.5rem" }}>
          {Object.entries(player.attributes).map(([attr, score]) => (
            <div
              key={attr}
              style={{
                padding: "var(--space-2)",
                backgroundColor: "var(--color-bg-elevated)",
                borderRadius: "var(--radius-sm)",
                textAlign: "center",
              }}
            >
              <div style={{ textTransform: "capitalize", fontSize: "var(--font-size-xs)", color: "var(--color-text-secondary)" }}>
                {attr}
              </div>
              <div style={{ fontSize: "var(--font-size-md)", fontWeight: "bold" }}>{score}</div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 style={{ fontSize: "var(--font-size-sm)", textTransform: "uppercase", color: "var(--color-text-muted)", marginBottom: "0.75rem" }}>
          Equipped Skills ({player.equipped_skills.length} / 4)
        </h3>
        {player.equipped_skills.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
            No combat skills equipped.
          </p>
        ) : (
          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {player.equipped_skills.map((skillId) => (
              <li
                key={skillId}
                style={{
                  padding: "var(--space-2) var(--space-3)",
                  backgroundColor: "var(--color-bg-elevated)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--font-size-sm)",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <span>{skillId}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
