import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import { generateCommandId } from "../../api/commands";
import type { AllowedCombatAction, CombatResponse, CombatState } from "../../api/schema";
import { CombatCommandBar } from "./CombatCommandBar";
import { CombatEnemyList } from "./CombatEnemyList";
import { CombatTurnTracker } from "./CombatTurnTracker";

export function CombatScreen(): React.JSX.Element {
  const { campaignId, saveId } = useParams<{ campaignId: string; saveId: string }>();
  const navigate = useNavigate();

  const [combat, setCombat] = useState<CombatState | null>(null);
  const [allowedActions, setAllowedActions] = useState<AllowedCombatAction[]>([]);
  const [revision, setRevision] = useState<number>(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [terminal, setTerminal] = useState<{ outcome: string | null } | null>(null);
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
        setCombat(resp.combat ?? null);
        setAllowedActions(resp.allowed_actions);
        setRevision(resp.revision);
        if (resp.combat) {
          const firstEnemy = Object.entries(resp.combat.participants).find(
            ([, p]) => p.side === "enemy" && p.hp.current > 0,
          );
          if (firstEnemy) setSelectedTargetId(firstEnemy[0]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load combat encounter");
      } finally {
        setLoading(false);
      }
    };

    fetchCombat();
  }, [campaignId, saveId]);

  const applyResponse = (resp: CombatResponse) => {
    if (resp.logs.length > 0) setLogs((prev) => [...prev, ...resp.logs]);
    setCombat(resp.combat ?? null);
    setAllowedActions(resp.allowed_actions);
    setRevision(resp.revision);
    if (resp.is_terminal) setTerminal({ outcome: resp.outcome ?? null });
  };

  const handleExecute = async (action: AllowedCombatAction) => {
    if (!campaignId || !saveId) return;
    setSubmitting(true);
    setError(null);
    const command_id = generateCommandId();
    const common = {
      campaign_id: campaignId,
      save_id: saveId,
      command_id,
      expected_revision: revision,
    };
    try {
      let resp: CombatResponse;
      switch (action.action_kind) {
        case "use_skill": {
          const targetIds =
            action.target_rule === "single_enemy" || action.target_rule === "single_ally"
              ? selectedTargetId
                ? [selectedTargetId]
                : []
              : action.valid_target_ids;
          resp = await defaultApiClient.useSkill({
            ...common,
            skill_id: action.skill_id as string,
            target_ids: targetIds,
          });
          break;
        }
        case "defend":
          resp = await defaultApiClient.defend(common);
          break;
        case "flee":
          resp = await defaultApiClient.flee(common);
          break;
        case "yield":
          resp = await defaultApiClient.yieldCombat(common);
          break;
      }
      applyResponse(resp);
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

  if (terminal || !combat) {
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
        <h1 style={{ marginBottom: "1rem" }}>
          {error ? "Encounter Error" : "⚔️ Combat Concluded"}
        </h1>
        {error ? (
          <p style={{ color: "var(--color-danger)", marginBottom: "1.5rem" }}>{error}</p>
        ) : (
          <p style={{ fontSize: "var(--font-size-lg)", marginBottom: "2rem" }}>
            Outcome: <strong>{terminal?.outcome ?? "Resolved"}</strong>
          </p>
        )}
        {logs.length > 0 && <CombatLog logs={logs} />}
        <Link
          to={`/play/${campaignId}/${saveId}`}
          style={{ color: "var(--color-accent)", fontWeight: "bold" }}
        >
          Return to exploration →
        </Link>
      </section>
    );
  }

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
        <button type="button" onClick={() => navigate(`/play/${campaignId}/${saveId}`)}>
          Leave
        </button>
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
        allowedActions={allowedActions}
        isPlayerTurn={isPlayerTurn}
        submitting={submitting}
        selectedTargetId={selectedTargetId}
        onExecute={handleExecute}
      />

      {error && (
        <p style={{ color: "var(--color-danger)", marginTop: "1rem" }}>{error}</p>
      )}

      <CombatLog logs={logs} />
    </section>
  );
}

function CombatLog({ logs }: { logs: string[] }): React.JSX.Element {
  return (
    <section
      aria-label="Combat Log"
      style={{
        marginTop: "1.5rem",
        padding: "var(--space-3)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-md)",
        fontSize: "var(--font-size-xs)",
      }}
    >
      <h3
        style={{
          textTransform: "uppercase",
          color: "var(--color-text-muted)",
          marginBottom: "0.5rem",
        }}
      >
        Combat Log
      </h3>
      {logs.length === 0 ? (
        <p style={{ color: "var(--color-text-muted)" }}>No actions yet.</p>
      ) : (
        <ol style={{ margin: 0, paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.15rem" }}>
          {logs.map((line, idx) => (
            <li key={idx}>{line}</li>
          ))}
        </ol>
      )}
    </section>
  );
}
