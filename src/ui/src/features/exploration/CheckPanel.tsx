import React from "react";

export interface PendingCheckData {
  check_id: string;
  skill_or_attribute: string;
  dc: number;
  stakes_description: string;
  allow_luck_reroll: boolean;
}

interface CheckPanelProps {
  check: PendingCheckData;
  submitting: boolean;
  onResolve: (useLuck: boolean) => void;
  onCancel: () => void;
}

export function CheckPanel({
  check,
  submitting,
  onResolve,
  onCancel,
}: CheckPanelProps): React.JSX.Element {
  return (
    <section
      aria-label="Pending Dice Check"
      style={{
        padding: "var(--space-4)",
        backgroundColor: "var(--color-bg-surface)",
        border: "2px solid var(--color-warning)",
        borderRadius: "var(--radius-lg)",
        marginBottom: "1.5rem",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <h2 style={{ fontSize: "var(--font-size-md)", color: "var(--color-warning)" }}>
          🎲 Skill Check Required
        </h2>
        <span
          style={{
            padding: "2px 8px",
            backgroundColor: "rgba(251, 191, 36, 0.15)",
            color: "var(--color-warning)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: "bold",
          }}
        >
          DC {check.dc}
        </span>
      </div>

      <div style={{ marginBottom: "1rem", fontSize: "var(--font-size-sm)" }}>
        <p style={{ marginBottom: "0.5rem" }}>
          <strong>Governing Trait:</strong>{" "}
          <span style={{ textTransform: "capitalize" }}>{check.skill_or_attribute}</span>
        </p>
        <p style={{ color: "var(--color-text-secondary)" }}>
          <strong>Stakes:</strong> {check.stakes_description}
        </p>
      </div>

      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
        <button
          type="button"
          disabled={submitting}
          onClick={() => onResolve(false)}
          style={{
            backgroundColor: "var(--color-accent)",
            color: "var(--color-bg-base)",
            fontWeight: "bold",
            fontSize: "var(--font-size-sm)",
          }}
        >
          {submitting ? "Rolling..." : "Roll d20 Check"}
        </button>

        {check.allow_luck_reroll && (
          <button
            type="button"
            disabled={submitting}
            onClick={() => onResolve(true)}
            style={{
              backgroundColor: "var(--color-warning)",
              color: "var(--color-bg-base)",
              fontWeight: "bold",
              fontSize: "var(--font-size-sm)",
            }}
          >
            {submitting ? "Rolling..." : "Spend Luck & Roll"}
          </button>
        )}

        <button
          type="button"
          disabled={submitting}
          onClick={onCancel}
          style={{
            backgroundColor: "transparent",
            color: "var(--color-text-secondary)",
            fontSize: "var(--font-size-sm)",
          }}
        >
          Cancel
        </button>
      </div>
    </section>
  );
}
