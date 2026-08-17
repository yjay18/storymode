import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import type { CombatStateResponse } from "../../api/schema";
import { CombatCommandBar } from "./CombatCommandBar";
import { CombatEnemyList } from "./CombatEnemyList";
import { CombatTurnTracker } from "./CombatTurnTracker";

export function CombatScreen(): React.JSX.Element {
  const { campaignId, saveId, combatId } = useParams<{
    campaignId: string;
    saveId: string;
    combatId: string;
  }>();
  const navigate = useNavigate();

  const [combatState, setCombatState] = useState<CombatStateResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);

  useEffect(() => {
    const fetchCombat = async () => {
      if (!campaignId || !saveId || !combatId) return;
      setLoading(true);
      setError(null);
      try {
        const cs = await defaultApiClient.getCombatState(campaignId, saveId, combatId);
        setCombatState(cs);
        const firstActive = cs.enemies.find((e) => !e.is_defeated);
        if (firstActive) {
          setSelectedTargetId(firstActive.enemy_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load combat encounter");
      } finally {
        setLoading(false);
      }
    };

    fetchCombat();
  }, [campaignId, saveId, combatId]);

  const handleCommand = async (_type: "skill" | "defend" | "flee" | "yield", _skillId?: string) => {
    if (!campaignId || !saveId || !combatId) return;
    setSubmitting(true);
    try {
      // Refresh combat state
      const updated = await defaultApiClient.getCombatState(campaignId, saveId, combatId);
      setCombatState(updated);
      if (updated.is_finished) {
        // Combat concluded
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Command failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <section aria-label="Tactical Combat">
        <p style={{ color: "var(--color-text-secondary)" }}>Entering tactical encounter...</p>
      </section>
    );
  }

  if (error || !combatState) {
    return (
      <section aria-label="Tactical Combat">
        <h1 style={{ color: "var(--color-danger)", marginBottom: "1rem" }}>Encounter Error</h1>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>{error}</p>
        <Link to={`/play/${campaignId}/${saveId}`} style={{ color: "var(--color-accent)" }}>
          ← Return to Exploration
        </Link>
      </section>
    );
  }

  if (combatState.is_finished) {
    return (
      <section
        aria-label="Combat Concluded"
        style={{
          padding: "3rem",
          backgroundColor: "var(--color-bg-surface)",
          borderRadius: "var(--radius-lg)",
          textAlign: "center",
          maxWidth: "600px",
          margin: "2rem auto",
        }}
      >
        <h1 style={{ marginBottom: "1rem", color: "var(--color-success)" }}>
          ⚔️ Combat Concluded
        </h1>
        <p style={{ fontSize: "var(--font-size-lg)", marginBottom: "2rem" }}>
          Outcome: <strong>{combatState.outcome || "Finished"}</strong>
        </p>
        <button
          type="button"
          onClick={() => navigate(`/play/${campaignId}/${saveId}`)}
          style={{
            backgroundColor: "var(--color-accent)",
            color: "var(--color-bg-base)",
            fontWeight: "bold",
            padding: "var(--space-3) var(--space-6)",
          }}
        >
          Resume Exploration →
        </button>
      </section>
    );
  }

  return (
    <section aria-label="Tactical Combat" style={{ maxWidth: "900px", margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h1>⚔️ Tactical Encounter</h1>
        <span
          style={{
            padding: "2px 8px",
            backgroundColor: "rgba(248, 113, 113, 0.15)",
            color: "var(--color-danger)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: "bold",
          }}
        >
          COMBAT ACTIVE
        </span>
      </div>

      <CombatTurnTracker
        round={combatState.round}
        turnOrder={combatState.turn_order}
        activeEntityId={combatState.active_entity_id}
        isPlayerTurn={combatState.is_player_turn}
      />

      <CombatEnemyList
        enemies={combatState.enemies}
        selectedTargetId={selectedTargetId}
        onSelectTarget={setSelectedTargetId}
      />

      <CombatCommandBar
        availableSkills={combatState.available_skills}
        canFlee={combatState.can_flee}
        canYield={combatState.can_yield}
        isPlayerTurn={combatState.is_player_turn}
        submitting={submitting}
        selectedTargetId={selectedTargetId}
        onExecuteCommand={handleCommand}
      />
    </section>
  );
}
