import React from "react";
import { Link } from "react-router-dom";
import type { CampaignSummary } from "../../api/schema";

interface CampaignListProps {
  campaigns: CampaignSummary[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function CampaignList({
  campaigns,
  loading,
  error,
  onRetry,
}: CampaignListProps): React.JSX.Element {
  if (loading) {
    return (
      <section aria-label="Campaign Catalog">
        <p style={{ color: "var(--color-text-secondary)" }}>Loading campaigns...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section aria-label="Campaign Catalog">
        <p style={{ color: "var(--color-danger)", marginBottom: "1rem" }}>{error}</p>
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      </section>
    );
  }

  if (campaigns.length === 0) {
    return (
      <section
        aria-label="Campaign Catalog"
        style={{
          textAlign: "center",
          padding: "3rem",
          backgroundColor: "var(--color-bg-surface)",
          borderRadius: "var(--radius-lg)",
          border: "1px dashed var(--color-border-subtle)",
        }}
      >
        <h2 style={{ marginBottom: "0.5rem", fontSize: "var(--font-size-xl)" }}>
          No Campaigns Found
        </h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>
          You don't have any published campaigns yet. Create your first world with the builder!
        </p>
        <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
          <Link
            to="/builder/guided"
            style={{
              display: "inline-block",
              padding: "var(--space-2) var(--space-4)",
              backgroundColor: "var(--color-accent)",
              color: "var(--color-bg-base)",
              fontWeight: "600",
              borderRadius: "var(--radius-md)",
              textDecoration: "none",
            }}
          >
            Guided Builder
          </Link>
          <Link
            to="/builder/quick"
            style={{
              display: "inline-block",
              padding: "var(--space-2) var(--space-4)",
              backgroundColor: "var(--color-bg-elevated)",
              color: "var(--color-text-primary)",
              borderRadius: "var(--radius-md)",
              textDecoration: "none",
            }}
          >
            Quick Prompt
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Campaign Catalog">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.5rem",
        }}
      >
        <h2>Available Worlds ({campaigns.length})</h2>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <Link
            to="/builder/guided"
            style={{
              padding: "var(--space-2) var(--space-3)",
              backgroundColor: "var(--color-accent)",
              color: "var(--color-bg-base)",
              fontWeight: "600",
              fontSize: "var(--font-size-sm)",
              borderRadius: "var(--radius-md)",
              textDecoration: "none",
            }}
          >
            + New Campaign
          </Link>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
          gap: "1.5rem",
        }}
      >
        {campaigns.map((camp) => (
          <article
            key={camp.campaign_id}
            style={{
              padding: "var(--space-4)",
              backgroundColor: "var(--color-bg-surface)",
              border: "1px solid var(--color-border-subtle)",
              borderRadius: "var(--radius-lg)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: "0.5rem",
                }}
              >
                <h3 style={{ fontSize: "var(--font-size-lg)" }}>{camp.title}</h3>
                <span
                  style={{
                    fontSize: "var(--font-size-xs)",
                    padding: "2px 6px",
                    borderRadius: "var(--radius-sm)",
                    backgroundColor:
                      camp.status === "published"
                        ? "rgba(52, 211, 153, 0.15)"
                        : "rgba(251, 191, 36, 0.15)",
                    color:
                      camp.status === "published"
                        ? "var(--color-success)"
                        : "var(--color-warning)",
                  }}
                >
                  {camp.status}
                </span>
              </div>
              <p
                style={{
                  fontSize: "var(--font-size-sm)",
                  color: "var(--color-text-secondary)",
                  marginBottom: "1rem",
                  lineHeight: "1.4",
                }}
              >
                {camp.theme}
              </p>
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderTop: "1px solid var(--color-border-subtle)",
                paddingTop: "0.75rem",
                fontSize: "var(--font-size-xs)",
                color: "var(--color-text-muted)",
              }}
            >
              <span>
                {camp.default_difficulty} • {camp.campaign_length}
              </span>
              <Link
                to={`/campaigns/${camp.campaign_id}`}
                style={{
                  color: "var(--color-accent)",
                  textDecoration: "none",
                  fontWeight: "600",
                }}
              >
                View Details →
              </Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
