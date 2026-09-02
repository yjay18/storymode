import React from "react";
import type { PlayerProgressionView } from "../../api/schema";

interface CharacterPanelProps {
  player: PlayerProgressionView;
}

export function CharacterPanel({ player }: CharacterPanelProps): React.JSX.Element {
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
          Level {player.level} • {player.xp} XP • {player.upgrade_tokens} tokens
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <div>
          <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
            Hit Points
          </span>
          <div
            style={{
              fontSize: "var(--font-size-lg)",
              fontWeight: "bold",
              color: "var(--color-success)",
            }}
          >
            {player.hp_current} / {player.hp_maximum}
          </div>
        </div>
        <div>
          <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
            Mana Pool
          </span>
          <div
            style={{
              fontSize: "var(--font-size-lg)",
              fontWeight: "bold",
              color: "var(--color-accent)",
            }}
          >
            {player.mana_current} / {player.mana_maximum}
          </div>
        </div>
      </div>

      <div>
        <h3
          style={{
            fontSize: "var(--font-size-sm)",
            textTransform: "uppercase",
            color: "var(--color-text-muted)",
            marginBottom: "0.75rem",
          }}
        >
          Known Skills ({player.known_skills.length})
        </h3>
        {player.known_skills.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
            No skills learned yet.
          </p>
        ) : (
          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {player.known_skills.map((skill) => {
              const equipped = player.combat_loadout.includes(skill.skill_id);
              return (
                <li
                  key={skill.skill_id}
                  style={{
                    padding: "var(--space-2) var(--space-3)",
                    backgroundColor: "var(--color-bg-elevated)",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "var(--font-size-sm)",
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span>
                    {skill.skill_id} (Lv {skill.current_level})
                  </span>
                  {equipped && (
                    <span style={{ color: "var(--color-accent)", fontSize: "var(--font-size-xs)" }}>
                      Equipped
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
