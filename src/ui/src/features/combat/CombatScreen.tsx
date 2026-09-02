import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import type { CombatViewResponse } from "../../api/schema";
import { CombatCommandBar } from "./CombatCommandBar";
import { CombatEnemyList } from "./CombatEnemyList";
import { CombatTurnTracker } from "./CombatTurnTracker";

export function CombatScreen(): React.JSX.Element {
  const { campaignId, saveId } = useParams<{ campaignId: string; saveId: string }>();
  const navigate = useNavigate();

  const [view, setView] = useState<CombatViewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);

  useEffect(() => {
    const fetchCombat = async () => {
      if (!campaignId || !saveId) return;
      setLoading(true);
      setError(null);
      try {
        const resp = await defaultApiClient.getCombatView(campaignId, saveId);
        setView(resp);
        const firstEnemy = resp.combat
          ? Object.entries(resp.combat.participants).find(
              ([, p]) => p.side === "enemy" && p.hp.current > 0,
            )
          : undefined;
        if (firstEnemy) {
          setSelectedTargetId(firstEnemy[0]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load combat encounter");
      } finally {
        setLoading(false);
      }
    };

    fetchCombat();
  }, [campaignId, saveId]);

  // PLAY-01 loads and renders the combat view; command posting arrives in PLAY-03.
  const handleCommand = async () => {
    if (!campaignId || !saveId) return;
    setSubmitting(true);
    try {
      setView(await defaultApiClient.getCombatView(campaignId, saveId));
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

  if (error || !view || !view.combat) {
    return (
      <section aria-label="Tactical Combat">
        <h1 style={{ color: "var(--color-danger)", marginBottom: "1rem" }}>
          {error ? "Encounter Error" : "No Active Combat"}
        </h1>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>{error}</p>
        <Link to={`/play/${campaignId}/${saveId}`} style={{ color: "var(--color-accent)" }}>
          ← Return to Exploration
        </Link>
      </section>
    );
  }

  const { combat, allowed_actions } = view;
  const activeEntityId = combat.order[combat.current_index] ?? "";
  const isPlayerTurn = combat.participants[activeEntityId]?.side === "party";

  const enemies = Object.entries(combat.participants)
    .filter(([, p]) => p.side === "enemy")
    .map(([id, p]) => ({
      enemy_id: id,
      name: id,
      hp: p.hp.current,
      max_hp: p.hp.maximum,
      is_defeated: p.hp.current <= 0,
    }));

  const availableSkills = allowed_actions
    .filter((a) => a.action_kind === "use_skill" && a.skill_id)
    .map((a) => a.skill_id as string);
  const canFlee = allowed_actions.some((a) => a.action_kind === "flee");
  const canYield = allowed_actions.some((a) => a.action_kind === "yield");

  return (
    <section aria-label="Tactical Combat" style={{ maxWidth: "900px", margin: "0 auto" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
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
        round={combat.round}
        turnOrder={combat.order}
        activeEntityId={activeEntityId}
        isPlayerTurn={isPlayerTurn}
      />

      <CombatEnemyList
        enemies={enemies}
        selectedTargetId={selectedTargetId}
        onSelectTarget={setSelectedTargetId}
      />

      <CombatCommandBar
        availableSkills={availableSkills}
        canFlee={canFlee}
        canYield={canYield}
        isPlayerTurn={isPlayerTurn}
        submitting={submitting}
        selectedTargetId={selectedTargetId}
        onExecuteCommand={handleCommand}
      />

      <div style={{ marginTop: "1rem" }}>
        <button type="button" onClick={() => navigate(`/play/${campaignId}/${saveId}`)}>
          Return to exploration
        </button>
      </div>
    </section>
  );
}
