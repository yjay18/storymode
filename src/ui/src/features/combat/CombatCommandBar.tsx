import React from "react";

interface CombatCommandBarProps {
  availableSkills: string[];
  canFlee: boolean;
  canYield: boolean;
  isPlayerTurn: boolean;
  submitting: boolean;
  selectedTargetId: string | null;
  onExecuteCommand: (type: "skill" | "defend" | "flee" | "yield", skillId?: string) => void;
}

export function CombatCommandBar({
  availableSkills,
  canFlee,
  canYield,
  isPlayerTurn,
  submitting,
  selectedTargetId,
  onExecuteCommand,
}: CombatCommandBarProps): React.JSX.Element {
  const disabled = !isPlayerTurn || submitting;

  return (
    <section
      aria-label="Combat Actions"
      style={{
        padding: "var(--space-4)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <h3 style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-muted)", textTransform: "uppercase", marginBottom: "0.75rem" }}>
        Tactical Commands
      </h3>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginBottom: "1rem" }}>
        {availableSkills.map((skill) => (
          <button
            key={skill}
            type="button"
            disabled={disabled || !selectedTargetId}
            onClick={() => onExecuteCommand("skill", skill)}
            style={{
              backgroundColor: "var(--color-accent)",
              color: "var(--color-bg-base)",
              fontWeight: "bold",
              fontSize: "var(--font-size-sm)",
            }}
          >
            Use {skill}
          </button>
        ))}

        <button
          type="button"
          disabled={disabled}
          onClick={() => onExecuteCommand("defend")}
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            color: "var(--color-text-primary)",
            fontSize: "var(--font-size-sm)",
          }}
        >
          🛡️ Defend (Guard)
        </button>

        {canFlee && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => onExecuteCommand("flee")}
            style={{
              backgroundColor: "transparent",
              border: "1px solid var(--color-warning)",
              color: "var(--color-warning)",
              fontSize: "var(--font-size-sm)",
            }}
          >
            🏃 Attempt Flee
          </button>
        )}

        {canYield && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => onExecuteCommand("yield")}
            style={{
              backgroundColor: "transparent",
              border: "1px solid var(--color-danger)",
              color: "var(--color-danger)",
              fontSize: "var(--font-size-sm)",
            }}
          >
            🏳️ Yield
          </button>
        )}
      </div>

      {!selectedTargetId && (
        <p style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
          Select a target enemy above to execute offensive skills.
        </p>
      )}
    </section>
  );
}
