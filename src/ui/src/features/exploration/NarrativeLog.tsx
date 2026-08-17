import React from "react";
import { ResultCard } from "./ResultCard";

export interface LogEntry {
  id: string;
  type: "player_action" | "result";
  content: string;
  status?: "success" | "check_required" | "rejected" | "combat_started";
  narration?: string;
  errorReason?: string;
}

interface NarrativeLogProps {
  entries: LogEntry[];
}

export function NarrativeLog({ entries }: NarrativeLogProps): React.JSX.Element {
  return (
    <section
      aria-label="Narrative Chronicle"
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        overflowY: "auto",
        maxHeight: "60vh",
        paddingRight: "0.5rem",
      }}
    >
      {entries.length === 0 ? (
        <div
          style={{
            padding: "2rem",
            textAlign: "center",
            color: "var(--color-text-muted)",
            backgroundColor: "var(--color-bg-surface)",
            borderRadius: "var(--radius-lg)",
            border: "1px dashed var(--color-border-subtle)",
          }}
        >
          Your adventure begins here. Describe your actions in the composer below.
        </div>
      ) : (
        entries.map((entry) => {
          if (entry.type === "player_action") {
            return (
              <div
                key={entry.id}
                style={{
                  alignSelf: "flex-end",
                  backgroundColor: "var(--color-bg-hover)",
                  padding: "var(--space-2) var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  maxWidth: "80%",
                  fontSize: "var(--font-size-sm)",
                  color: "var(--color-text-primary)",
                  borderRight: "3px solid var(--color-accent)",
                }}
              >
                <strong>You:</strong> {entry.content}
              </div>
            );
          }

          return (
            <ResultCard
              key={entry.id}
              status={entry.status || "success"}
              summary={entry.content}
              narration={entry.narration}
              errorReason={entry.errorReason}
            />
          );
        })
      )}
    </section>
  );
}
