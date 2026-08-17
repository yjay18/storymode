import React from "react";
import type { ValidationReport } from "../../api/schema";

interface ValidationReportProps {
  report: ValidationReport | null;
  loading: boolean;
  onRefresh: () => void;
}

export function ValidationReportView({
  report,
  loading,
  onRefresh,
}: ValidationReportProps): React.JSX.Element {
  if (loading) {
    return (
      <div
        style={{
          padding: "var(--space-4)",
          backgroundColor: "var(--color-bg-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <p style={{ color: "var(--color-text-secondary)" }}>Running validation checks...</p>
      </div>
    );
  }

  if (!report) {
    return (
      <div
        style={{
          padding: "var(--space-4)",
          backgroundColor: "var(--color-bg-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <button type="button" onClick={onRefresh}>
          Run Validation Report
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "var(--space-4)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-lg)",
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
        <h3 style={{ fontSize: "var(--font-size-md)" }}>Validation & Publish Readiness</h3>
        <button
          type="button"
          onClick={onRefresh}
          style={{ padding: "var(--space-1) var(--space-3)", fontSize: "var(--font-size-xs)" }}
        >
          Re-validate
        </button>
      </div>

      <div style={{ display: "flex", gap: "1.5rem", marginBottom: "1rem" }}>
        <div>
          Status:{" "}
          <strong style={{ color: report.is_valid ? "var(--color-success)" : "var(--color-danger)" }}>
            {report.is_valid ? "Valid" : "Invalid"}
          </strong>
        </div>
        <div>
          Publish Ready:{" "}
          <strong
            style={{
              color: report.is_publish_ready ? "var(--color-success)" : "var(--color-warning)",
            }}
          >
            {report.is_publish_ready ? "Ready" : "Not Ready"}
          </strong>
        </div>
      </div>

      {report.errors.length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <h4 style={{ color: "var(--color-danger)", fontSize: "var(--font-size-sm)", marginBottom: "0.5rem" }}>
            Errors ({report.errors.length}):
          </h4>
          <ul style={{ paddingLeft: "1.5rem", color: "var(--color-danger)", fontSize: "var(--font-size-xs)" }}>
            {report.errors.map((e, idx) => (
              <li key={idx}>
                [{e.stage}] {e.code}: {e.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.warnings.length > 0 && (
        <div>
          <h4 style={{ color: "var(--color-warning)", fontSize: "var(--font-size-sm)", marginBottom: "0.5rem" }}>
            Warnings ({report.warnings.length}):
          </h4>
          <ul style={{ paddingLeft: "1.5rem", color: "var(--color-warning)", fontSize: "var(--font-size-xs)" }}>
            {report.warnings.map((w, idx) => (
              <li key={idx}>
                [{w.stage}] {w.code}: {w.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.errors.length === 0 && report.warnings.length === 0 && (
        <p style={{ color: "var(--color-success)", fontSize: "var(--font-size-sm)" }}>
          ✓ All cross-file schemas, references, graphs, and balance constraints are 100% valid!
        </p>
      )}
    </div>
  );
}
