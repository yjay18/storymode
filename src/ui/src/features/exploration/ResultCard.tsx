import React from "react";

interface ResultCardProps {
  status: "success" | "check_required" | "rejected" | "combat_started";
  summary: string;
  narration?: string;
  errorReason?: string;
  details?: string[];
}

export function ResultCard({
  status,
  summary,
  narration,
  errorReason,
  details,
}: ResultCardProps): React.JSX.Element {
  let borderColor = "var(--color-border-subtle)";
  let badgeText = "Action Result";
  let badgeColor = "var(--color-text-muted)";

  if (status === "success") {
    borderColor = "var(--color-success)";
    badgeText = "Success";
    badgeColor = "var(--color-success)";
  } else if (status === "check_required") {
    borderColor = "var(--color-warning)";
    badgeText = "Check Required";
    badgeColor = "var(--color-warning)";
  } else if (status === "rejected") {
    borderColor = "var(--color-danger)";
    badgeText = "Action Rejected";
    badgeColor = "var(--color-danger)";
  } else if (status === "combat_started") {
    borderColor = "var(--color-danger)";
    badgeText = "Combat Encounter";
    badgeColor = "var(--color-danger)";
  }

  return (
    <article
      aria-label={badgeText}
      style={{
        padding: "var(--space-3) var(--space-4)",
        backgroundColor: "var(--color-bg-elevated)",
        borderLeft: `4px solid ${borderColor}`,
        borderRadius: "var(--radius-md)",
        marginBottom: "1rem",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "0.25rem",
        }}
      >
        <strong style={{ fontSize: "var(--font-size-xs)", color: badgeColor }}>
          {badgeText.toUpperCase()}
        </strong>
      </div>

      <p style={{ fontWeight: "600", fontSize: "var(--font-size-sm)", marginBottom: "0.5rem" }}>
        {summary}
      </p>

      {details && details.length > 0 && (
        <dl
          aria-label="Roll breakdown"
          style={{
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            columnGap: "0.75rem",
            rowGap: "0.15rem",
            fontSize: "var(--font-size-xs)",
            margin: "0 0 0.5rem",
          }}
        >
          {details.map((line) => {
            const [label, ...rest] = line.split(":");
            return (
              <React.Fragment key={line}>
                <dt style={{ color: "var(--color-text-muted)" }}>{label}</dt>
                <dd style={{ margin: 0, fontWeight: "600" }}>{rest.join(":").trim()}</dd>
              </React.Fragment>
            );
          })}
        </dl>
      )}

      {narration && (
        <p
          style={{
            fontSize: "var(--font-size-sm)",
            color: "var(--color-text-secondary)",
            fontStyle: "italic",
            lineHeight: "1.4",
          }}
        >
          "{narration}"
        </p>
      )}

      {errorReason && (
        <p
          style={{
            fontSize: "var(--font-size-xs)",
            color: "var(--color-danger)",
            marginTop: "0.5rem",
          }}
        >
          Reason: {errorReason}
        </p>
      )}
    </article>
  );
}
