import React from "react";
import type { HealthResponse } from "../../api/schema";

interface PreflightProps {
  health: HealthResponse | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function PreflightCard({
  health,
  loading,
  error,
  onRetry,
}: PreflightProps): React.JSX.Element {
  if (loading) {
    return (
      <section
        aria-label="System Status"
        style={{
          padding: "var(--space-4)",
          backgroundColor: "var(--color-bg-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-lg)",
          marginBottom: "var(--space-6)",
        }}
      >
        <h2>Checking local system readiness...</h2>
      </section>
    );
  }

  if (error || !health) {
    return (
      <section
        aria-label="System Status"
        style={{
          padding: "var(--space-4)",
          backgroundColor: "var(--color-bg-surface)",
          border: "1px solid var(--color-danger)",
          borderRadius: "var(--radius-lg)",
          marginBottom: "var(--space-6)",
        }}
      >
        <h2 style={{ color: "var(--color-danger)", marginBottom: "0.5rem" }}>
          Local Service Unavailable
        </h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "1rem" }}>
          {error || "Could not reach local Storymode backend. Make sure the local server is running."}
        </p>
        <button type="button" onClick={onRetry}>
          Retry Connection
        </button>
      </section>
    );
  }

  return (
    <section
      aria-label="System Readiness Status"
      style={{
        padding: "var(--space-4) var(--space-6)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-lg)",
        marginBottom: "var(--space-6)",
      }}
    >
      <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "1rem" }}>
        Local System Readiness
      </h2>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "1rem",
        }}
      >
        {/* Deterministic Core */}
        <div
          style={{
            padding: "var(--space-3)",
            backgroundColor: "var(--color-bg-elevated)",
            borderRadius: "var(--radius-md)",
            borderLeft: "4px solid var(--color-success)",
          }}
        >
          <div style={{ fontWeight: "600", fontSize: "var(--font-size-sm)" }}>Core Engine</div>
          <div style={{ color: "var(--color-success)", fontSize: "var(--font-size-xs)" }}>
            Ready (v{health.version})
          </div>
        </div>

        {/* Ollama Reachability */}
        <div
          style={{
            padding: "var(--space-3)",
            backgroundColor: "var(--color-bg-elevated)",
            borderRadius: "var(--radius-md)",
            borderLeft: `4px solid ${
              health.ollama_reachable ? "var(--color-success)" : "var(--color-warning)"
            }`,
          }}
        >
          <div style={{ fontWeight: "600", fontSize: "var(--font-size-sm)" }}>Ollama Service</div>
          <div
            style={{
              color: health.ollama_reachable ? "var(--color-success)" : "var(--color-warning)",
              fontSize: "var(--font-size-xs)",
            }}
          >
            {health.ollama_reachable ? "Connected (Loopback)" : "Disconnected / Offline"}
          </div>
        </div>

        {/* Text Model */}
        <div
          style={{
            padding: "var(--space-3)",
            backgroundColor: "var(--color-bg-elevated)",
            borderRadius: "var(--radius-md)",
            borderLeft: `4px solid ${
              health.model_text_available ? "var(--color-success)" : "var(--color-danger)"
            }`,
          }}
        >
          <div style={{ fontWeight: "600", fontSize: "var(--font-size-sm)" }}>Text LLM</div>
          <div
            style={{
              color: health.model_text_available ? "var(--color-success)" : "var(--color-danger)",
              fontSize: "var(--font-size-xs)",
            }}
          >
            {health.model_text_available
              ? "Available"
              : "Unavailable (Model generation disabled)"}
          </div>
        </div>

        {/* Image Model */}
        <div
          style={{
            padding: "var(--space-3)",
            backgroundColor: "var(--color-bg-elevated)",
            borderRadius: "var(--radius-md)",
            borderLeft: `4px solid ${
              health.model_image_available ? "var(--color-success)" : "var(--color-warning)"
            }`,
          }}
        >
          <div style={{ fontWeight: "600", fontSize: "var(--font-size-sm)" }}>Image Model</div>
          <div
            style={{
              color: health.model_image_available ? "var(--color-success)" : "var(--color-warning)",
              fontSize: "var(--font-size-xs)",
            }}
          >
            {health.model_image_available ? "Available" : "Optional / Missing"}
          </div>
        </div>
      </div>
    </section>
  );
}
