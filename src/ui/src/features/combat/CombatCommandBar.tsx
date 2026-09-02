import React from "react";
import type { AllowedCombatAction } from "../../api/schema";

interface CombatCommandBarProps {
  allowedActions: AllowedCombatAction[];
  isPlayerTurn: boolean;
  submitting: boolean;
  selectedTargetId: string | null;
  onExecute: (action: AllowedCombatAction) => void;
}

function needsManualTarget(action: AllowedCombatAction): boolean {
  return action.target_rule === "single_enemy" || action.target_rule === "single_ally";
}

export function CombatCommandBar({
  allowedActions,
  isPlayerTurn,
  submitting,
  selectedTargetId,
  onExecute,
}: CombatCommandBarProps): React.JSX.Element {
  const baseDisabled = !isPlayerTurn || submitting;

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
      <h3
        style={{
          fontSize: "var(--font-size-sm)",
          color: "var(--color-text-muted)",
          textTransform: "uppercase",
          marginBottom: "0.75rem",
        }}
      >
        Tactical Commands
      </h3>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginBottom: "1rem" }}>
        {allowedActions.map((action, idx) => {
          if (action.action_kind === "use_skill") {
            const missingTarget = needsManualTarget(action) && !selectedTargetId;
            return (
              <button
                key={action.skill_id ?? `skill-${idx}`}
                type="button"
                disabled={baseDisabled || missingTarget}
                onClick={() => onExecute(action)}
                style={{
                  backgroundColor: "var(--color-accent)",
                  color: "var(--color-bg-base)",
                  fontWeight: "bold",
                  fontSize: "var(--font-size-sm)",
                }}
              >
                Use {action.skill_name ?? action.skill_id} · {action.mana_cost} MP
                {action.target_rule ? ` · ${action.target_rule}` : ""}
              </button>
            );
          }

          const label =
            action.action_kind === "defend"
              ? "🛡️ Defend"
              : action.action_kind === "flee"
                ? "🏃 Flee"
                : "🏳️ Yield";
          return (
            <button
              key={action.action_kind}
              type="button"
              disabled={baseDisabled}
              onClick={() => onExecute(action)}
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                color: "var(--color-text-primary)",
                fontSize: "var(--font-size-sm)",
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      {allowedActions.some((a) => a.action_kind === "use_skill" && needsManualTarget(a)) &&
        !selectedTargetId && (
          <p style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
            Select a target enemy above to use a targeted skill.
          </p>
        )}
    </section>
  );
}
