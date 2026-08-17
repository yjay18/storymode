import React from "react";
import type { DraftStage, DraftStageState, StageStatus } from "../../api/schema";

const STAGE_LABELS: Record<DraftStage, string> = {
  meta_style: "1. Meta & Style Bible",
  rules: "2. World Rules & Factions",
  areas: "3. Geography & Areas",
  plot: "4. Plot & Milestones",
  characters: "5. Characters & Companions",
  skills: "6. Skills, Items & Balance",
  review: "7. Review & Validation",
};

interface GenerationProgressProps {
  stages: Record<DraftStage, DraftStageState>;
  generating: boolean;
  onGenerate: (stage?: DraftStage) => void;
  onCancel: () => void;
}

function getStatusBadge(status: StageStatus) {
  switch (status) {
    case "valid":
      return <span style={{ color: "var(--color-success)" }}>✓ Valid</span>;
    case "running":
      return <span style={{ color: "var(--color-accent)" }}>⏳ Generating...</span>;
    case "invalid":
      return <span style={{ color: "var(--color-danger)" }}>✗ Errors</span>;
    case "cancelled":
      return <span style={{ color: "var(--color-warning)" }}>⏹ Cancelled</span>;
    default:
      return <span style={{ color: "var(--color-text-muted)" }}>Pending</span>;
  }
}

export function GenerationProgress({
  stages,
  generating,
  onGenerate,
  onCancel,
}: GenerationProgressProps): React.JSX.Element {
  const stageKeys: DraftStage[] = [
    "meta_style",
    "rules",
    "areas",
    "plot",
    "characters",
    "skills",
    "review",
  ];

  return (
    <div
      style={{
        padding: "var(--space-4)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
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
        <h2 style={{ fontSize: "var(--font-size-lg)" }}>Campaign Generation Stages</h2>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {generating ? (
            <button
              type="button"
              onClick={onCancel}
              style={{
                backgroundColor: "var(--color-warning)",
                color: "var(--color-bg-base)",
                fontWeight: "600",
              }}
            >
              Cancel Generation
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onGenerate()}
              style={{
                backgroundColor: "var(--color-accent)",
                color: "var(--color-bg-base)",
                fontWeight: "600",
              }}
            >
              Start / Continue All Stages
            </button>
          )}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {stageKeys.map((k) => {
          const st = stages[k] || {
            stage: k,
            status: "not_started",
            attempts: 0,
            diagnostics: [],
          };

          return (
            <div
              key={k}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "var(--space-3)",
                backgroundColor: "var(--color-bg-elevated)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div>
                <strong style={{ fontSize: "var(--font-size-sm)" }}>{STAGE_LABELS[k]}</strong>
                {st.attempts > 0 && (
                  <span
                    style={{
                      fontSize: "var(--font-size-xs)",
                      color: "var(--color-text-muted)",
                      marginLeft: "0.75rem",
                    }}
                  >
                    (Attempts: {st.attempts})
                  </span>
                )}
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                <span style={{ fontSize: "var(--font-size-sm)", fontWeight: "600" }}>
                  {getStatusBadge(st.status)}
                </span>
                {!generating && st.status !== "valid" && (
                  <button
                    type="button"
                    onClick={() => onGenerate(k)}
                    style={{
                      padding: "var(--space-1) var(--space-2)",
                      fontSize: "var(--font-size-xs)",
                    }}
                  >
                    Run Stage
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
