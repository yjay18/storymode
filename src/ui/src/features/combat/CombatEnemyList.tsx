import React from "react";

export interface CombatEnemy {
  enemy_id: string;
  name: string;
  hp: number;
  max_hp: number;
  is_defeated: boolean;
}

interface CombatEnemyListProps {
  enemies: CombatEnemy[];
  selectedTargetId: string | null;
  onSelectTarget: (id: string) => void;
}

export function CombatEnemyList({
  enemies,
  selectedTargetId,
  onSelectTarget,
}: CombatEnemyListProps): React.JSX.Element {
  return (
    <section aria-label="Hostile Encounters" style={{ marginBottom: "1.5rem" }}>
      <h3 style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-muted)", textTransform: "uppercase", marginBottom: "0.75rem" }}>
        Enemies ({enemies.filter((e) => !e.is_defeated).length} Active)
      </h3>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
        {enemies.map((enemy) => {
          const isSelected = enemy.enemy_id === selectedTargetId;
          const hpPercent = Math.max(0, Math.round((enemy.hp / enemy.max_hp) * 100));

          return (
            <div
              key={enemy.enemy_id}
              onClick={() => !enemy.is_defeated && onSelectTarget(enemy.enemy_id)}
              style={{
                padding: "var(--space-3) var(--space-4)",
                backgroundColor: isSelected ? "var(--color-bg-hover)" : "var(--color-bg-surface)",
                border: isSelected ? "2px solid var(--color-accent)" : "1px solid var(--color-border-subtle)",
                borderRadius: "var(--radius-lg)",
                cursor: enemy.is_defeated ? "not-allowed" : "pointer",
                opacity: enemy.is_defeated ? 0.4 : 1,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <strong style={{ fontSize: "var(--font-size-sm)" }}>{enemy.name}</strong>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                  {enemy.is_defeated ? "Defeated" : `${enemy.hp} / ${enemy.max_hp} HP`}
                </span>
              </div>

              {!enemy.is_defeated && (
                <div
                  style={{
                    height: "6px",
                    backgroundColor: "var(--color-bg-base)",
                    borderRadius: "3px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${hpPercent}%`,
                      height: "100%",
                      backgroundColor: "var(--color-danger)",
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
