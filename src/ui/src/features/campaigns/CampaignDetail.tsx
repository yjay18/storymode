import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import type { CampaignSummary, SaveSlotSummary } from "../../api/schema";

export function CampaignDetail(): React.JSX.Element {
  const { campaignId } = useParams<{ campaignId: string }>();
  const navigate = useNavigate();

  const [campaign, setCampaign] = useState<CampaignSummary | null>(null);
  const [saves, setSaves] = useState<SaveSlotSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // New Save creation state
  const [showNewSave, setShowNewSave] = useState<boolean>(false);
  const [playerName, setPlayerName] = useState<string>("");
  const [creatingSave, setCreatingSave] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      if (!campaignId) return;
      setLoading(true);
      setError(null);
      try {
        const camp = await defaultApiClient.getCampaign(campaignId);
        setCampaign(camp);
        const saveList = await defaultApiClient.listSaves(campaignId);
        setSaves(saveList);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load campaign");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [campaignId]);

  const handleCreateSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!campaignId || !playerName.trim()) return;

    setCreatingSave(true);
    setCreateError(null);
    try {
      const newSave = await defaultApiClient.createSave(campaignId, {
        player_name: playerName.trim(),
        background_id: "scout",
        attributes: {
          brawn: 2,
          finesse: 3,
          wit: 2,
          resolve: 2,
          presence: 1,
        },
      });
      navigate(`/play/${campaignId}/${newSave.save_id}`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create save");
      setCreatingSave(false);
    }
  };

  if (loading) {
    return (
      <section aria-label="Campaign Details">
        <p style={{ color: "var(--color-text-secondary)" }}>Loading campaign details...</p>
      </section>
    );
  }

  if (error || !campaign) {
    return (
      <section aria-label="Campaign Details">
        <h1 style={{ color: "var(--color-danger)", marginBottom: "1rem" }}>Error Loading Campaign</h1>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>{error}</p>
        <Link to="/" style={{ color: "var(--color-accent)", textDecoration: "underline" }}>
          ← Back to Campaign Library
        </Link>
      </section>
    );
  }

  return (
    <section aria-label="Campaign Details">
      <div style={{ marginBottom: "2rem" }}>
        <Link to="/" style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-sm)" }}>
          ← Back to Library
        </Link>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: "0.5rem",
          }}
        >
          <h1>{campaign.title}</h1>
          <span
            style={{
              padding: "4px 8px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "rgba(52, 211, 153, 0.15)",
              color: "var(--color-success)",
              fontSize: "var(--font-size-xs)",
              fontWeight: "600",
            }}
          >
            {campaign.status}
          </span>
        </div>
        <p
          style={{
            color: "var(--color-text-secondary)",
            fontSize: "var(--font-size-lg)",
            marginTop: "0.5rem",
          }}
        >
          {campaign.theme}
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "2rem",
        }}
      >
        {/* World Synopsis */}
        <div
          style={{
            padding: "var(--space-4)",
            backgroundColor: "var(--color-bg-surface)",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--color-border-subtle)",
          }}
        >
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "1rem" }}>
            World Information
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div>
              <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-sm)" }}>
                Difficulty:
              </span>{" "}
              <strong>{campaign.default_difficulty}</strong>
            </div>
            <div>
              <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-sm)" }}>
                Length:
              </span>{" "}
              <strong>{campaign.campaign_length}</strong>
            </div>
            <div>
              <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-sm)" }}>
                Source:
              </span>{" "}
              <strong>{campaign.source_type}</strong>
            </div>
            {campaign.source_summary && (
              <p
                style={{
                  color: "var(--color-text-secondary)",
                  fontSize: "var(--font-size-sm)",
                  marginTop: "0.5rem",
                }}
              >
                {campaign.source_summary}
              </p>
            )}
          </div>
        </div>

        {/* Save Slots */}
        <div
          style={{
            padding: "var(--space-4)",
            backgroundColor: "var(--color-bg-surface)",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--color-border-subtle)",
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
            <h2 style={{ fontSize: "var(--font-size-lg)" }}>Saved Games</h2>
            {!showNewSave && (
              <button
                type="button"
                onClick={() => setShowNewSave(true)}
                style={{
                  backgroundColor: "var(--color-accent)",
                  color: "var(--color-bg-base)",
                  fontWeight: "600",
                  fontSize: "var(--font-size-xs)",
                }}
              >
                + New Hero
              </button>
            )}
          </div>

          {showNewSave && (
            <form
              onSubmit={handleCreateSave}
              style={{
                padding: "var(--space-3)",
                backgroundColor: "var(--color-bg-elevated)",
                borderRadius: "var(--radius-md)",
                marginBottom: "1rem",
              }}
            >
              <label
                htmlFor="player-name-input"
                style={{
                  display: "block",
                  fontSize: "var(--font-size-sm)",
                  marginBottom: "0.25rem",
                }}
              >
                Hero Name:
              </label>
              <input
                id="player-name-input"
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                placeholder="e.g. Alistair"
                required
                maxLength={50}
                style={{ marginBottom: "0.75rem" }}
              />
              {createError && (
                <p
                  style={{
                    color: "var(--color-danger)",
                    fontSize: "var(--font-size-xs)",
                    marginBottom: "0.5rem",
                  }}
                >
                  {createError}
                </p>
              )}
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button
                  type="submit"
                  disabled={creatingSave || !playerName.trim()}
                  style={{
                    backgroundColor: "var(--color-accent)",
                    color: "var(--color-bg-base)",
                    fontWeight: "600",
                  }}
                >
                  {creatingSave ? "Creating..." : "Start Adventure"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowNewSave(false)}
                  style={{ backgroundColor: "transparent", color: "var(--color-text-secondary)" }}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {saves.length === 0 && !showNewSave ? (
            <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
              No save files for this campaign yet. Click "+ New Hero" to start playing!
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {saves.map((s) => (
                <div
                  key={s.save_id}
                  style={{
                    padding: "var(--space-3)",
                    backgroundColor: "var(--color-bg-elevated)",
                    borderRadius: "var(--radius-md)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: "600" }}>{s.player_name}</div>
                    <div
                      style={{
                        fontSize: "var(--font-size-xs)",
                        color: "var(--color-text-muted)",
                      }}
                    >
                      Slot {s.slot_number} • Area: {s.current_area_id} • Rev {s.revision}
                    </div>
                  </div>
                  <Link
                    to={`/play/${campaignId}/${s.save_id}`}
                    style={{
                      padding: "var(--space-1) var(--space-3)",
                      backgroundColor: "var(--color-accent)",
                      color: "var(--color-bg-base)",
                      borderRadius: "var(--radius-sm)",
                      textDecoration: "none",
                      fontSize: "var(--font-size-xs)",
                      fontWeight: "600",
                    }}
                  >
                    Continue →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
