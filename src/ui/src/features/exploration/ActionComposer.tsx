import React, { useState } from "react";

interface ActionComposerProps {
  disabled: boolean;
  submitting: boolean;
  onSubmit: (input: string) => void;
}

const MAX_ACTION_CHARS = 500;

export function ActionComposer({
  disabled,
  submitting,
  onSubmit,
}: ActionComposerProps): React.JSX.Element {
  const [input, setInput] = useState<string>("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled || submitting) return;
    onSubmit(input.trim());
    setInput("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      aria-label="Action Composer"
      style={{
        padding: "var(--space-4)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <label
        htmlFor="exploration-action-input"
        style={{
          display: "block",
          fontWeight: "600",
          fontSize: "var(--font-size-sm)",
          marginBottom: "0.5rem",
        }}
      >
        What do you want to do?
      </label>

      <textarea
        id="exploration-action-input"
        rows={3}
        value={input}
        disabled={disabled || submitting}
        onChange={(e) => setInput(e.target.value.slice(0, MAX_ACTION_CHARS))}
        placeholder="e.g. Inspect the ancient crest above the archway, or talk to the innkeeper..."
        style={{ marginBottom: "0.5rem", resize: "vertical" }}
      />

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span
          style={{
            fontSize: "var(--font-size-xs)",
            color: input.length >= MAX_ACTION_CHARS ? "var(--color-danger)" : "var(--color-text-muted)",
          }}
        >
          {input.length} / {MAX_ACTION_CHARS} characters
        </span>

        <button
          type="submit"
          disabled={disabled || submitting || !input.trim()}
          style={{
            backgroundColor: "var(--color-accent)",
            color: "var(--color-bg-base)",
            fontWeight: "bold",
            fontSize: "var(--font-size-sm)",
          }}
        >
          {submitting ? "Interpreting Intent..." : "Take Action →"}
        </button>
      </div>
    </form>
  );
}
