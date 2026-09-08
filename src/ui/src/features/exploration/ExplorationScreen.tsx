import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import { generateCommandId } from "../../api/commands";
import { ApiConflictError, ApiHttpError } from "../../api/errors";
import type { EncounterView, PendingCheck, SaveSummaryResponse } from "../../api/schema";
import { CharacterPanel } from "../character/CharacterPanel";
import { ActionComposer } from "./ActionComposer";
import { CheckPanel } from "./CheckPanel";
import { ContextRail } from "./ContextRail";
import { LogEntry, NarrativeLog } from "./NarrativeLog";
import { RollHistory, RollHistoryItem } from "./RollHistory";

function isInterpreterUnavailable(err: unknown): boolean {
  return (
    err instanceof ApiHttpError &&
    (err.status === 503 || err.message.toLowerCase().includes("interpreter"))
  );
}

export function ExplorationScreen(): React.JSX.Element {
  const { campaignId, saveId } = useParams<{ campaignId: string; saveId: string }>();
  const navigate = useNavigate();

  const [state, setState] = useState<SaveSummaryResponse | null>(null);
  const [encounters, setEncounters] = useState<EncounterView[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [engaging, setEngaging] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [narratorOffline, setNarratorOffline] = useState<boolean>(false);
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [pendingCheck, setPendingCheck] = useState<PendingCheck | null>(null);
  const [rollHistory, setRollHistory] = useState<RollHistoryItem[]>([]);

  useEffect(() => {
    const loadState = async () => {
      if (!campaignId || !saveId) return;
      setLoading(true);
      setError(null);
      try {
        const save = await defaultApiClient.getSave(campaignId, saveId);
        setState(save);

        // Resume an in-progress combat rather than stranding the player in exploration.
        const combatView = await defaultApiClient.getCombatView(campaignId, saveId);
        if (combatView.combat) {
          navigate(`/play/${campaignId}/${saveId}/combat`);
          return;
        }

        const campaign = await defaultApiClient.getCampaign(campaignId);
        const area = campaign.areas.find((a) => a.id === save.current_area_id);
        setEncounters(area?.encounters ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load adventure state");
      } finally {
        setLoading(false);
      }
    };

    loadState();
  }, [campaignId, saveId, navigate]);

  const handleEngage = async (encounterId: string) => {
    if (!campaignId || !saveId || !state) return;
    setEngaging(true);
    try {
      await defaultApiClient.startCombat({
        campaign_id: campaignId,
        save_id: saveId,
        encounter_id: encounterId,
        command_id: generateCommandId(),
        expected_revision: state.revision,
      });
      navigate(`/play/${campaignId}/${saveId}/combat`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start combat");
      setEngaging(false);
    }
  };

  const refresh = async (): Promise<SaveSummaryResponse | null> => {
    if (!campaignId || !saveId) return null;
    const fresh = await defaultApiClient.getSave(campaignId, saveId);
    setState(fresh);
    return fresh;
  };

  const appendEntry = (entry: LogEntry) => setEntries((prev) => [...prev, entry]);

  const handleTakeAction = async (playerText: string) => {
    if (!campaignId || !saveId || !state) return;

    appendEntry({ id: `user-${Date.now()}`, type: "player_action", content: playerText });
    setSubmitting(true);
    setNarratorOffline(false);

    const submitOnce = (revision: number) =>
      defaultApiClient.submitAction({
        campaign_id: campaignId,
        save_id: saveId,
        command_id: generateCommandId(),
        expected_revision: revision,
        player_text: playerText,
      });

    try {
      let resp;
      try {
        resp = await submitOnce(state.revision);
      } catch (err) {
        if (err instanceof ApiConflictError) {
          const fresh = await refresh(); // 409: refetch then retry once
          resp = await submitOnce(fresh?.revision ?? state.revision);
        } else {
          throw err;
        }
      }

      if (resp.rejection_reason) {
        appendEntry({
          id: `res-${Date.now()}`,
          type: "result",
          content: "Action rejected",
          status: "rejected",
          errorReason: resp.rejection_reason,
        });
      } else if (resp.has_pending_check && resp.pending_check) {
        setPendingCheck(resp.pending_check);
      } else {
        appendEntry({
          id: `res-${Date.now()}`,
          type: "result",
          content: "You take action.",
          status: "success",
          narration: resp.narration ?? undefined,
        });
      }

      await refresh();
    } catch (err) {
      if (isInterpreterUnavailable(err)) {
        setNarratorOffline(true);
      } else {
        appendEntry({
          id: `err-${Date.now()}`,
          type: "result",
          content: "Action failed",
          status: "rejected",
          errorReason: err instanceof Error ? err.message : "Transport error",
        });
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolveCheck = async (useLuck: boolean) => {
    if (!campaignId || !saveId || !state || !pendingCheck) return;
    const check = pendingCheck;
    setSubmitting(true);

    const resolveOnce = (revision: number) =>
      defaultApiClient.resolveCheck({
        campaign_id: campaignId,
        save_id: saveId,
        command_id: generateCommandId(),
        expected_revision: revision,
        use_luck: useLuck,
      });

    try {
      let resp;
      try {
        resp = await resolveOnce(state.revision);
      } catch (err) {
        if (err instanceof ApiConflictError) {
          const fresh = await refresh(); // 409: refetch then retry once
          resp = await resolveOnce(fresh?.revision ?? state.revision);
        } else {
          throw err;
        }
      }

      const modText =
        Object.entries(check.named_modifiers)
          .map(([name, value]) => `${name} ${value >= 0 ? "+" : ""}${value}`)
          .join(", ") || "none";

      setRollHistory((prev) => [
        ...prev,
        {
          id: `roll-${Date.now()}`,
          checkId: check.check_id,
          trait: check.stat ?? check.skill_id ?? check.semantic_difficulty,
          dc: check.final_dc,
          total: resp.roll,
          outcome: resp.band,
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);

      appendEntry({
        id: `res-${Date.now()}`,
        type: "result",
        content: `Check ${resp.band}`,
        status: "success",
        narration: resp.narration ?? undefined,
        details: [
          `Die: ${resp.roll}`,
          `Modifiers: ${modText}`,
          `Total: ${resp.roll}`,
          `DC: ${check.final_dc}`,
          `Outcome: ${resp.band}${useLuck ? " (luck spent)" : ""}`,
        ],
      });

      setPendingCheck(null);
      await refresh();
    } catch (err) {
      appendEntry({
        id: `err-${Date.now()}`,
        type: "result",
        content: "Check resolution failed",
        status: "rejected",
        errorReason: err instanceof Error ? err.message : "Transport error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelCheck = async () => {
    if (!campaignId || !saveId || !state || !pendingCheck) return;
    setSubmitting(true);
    try {
      await defaultApiClient.cancelCheck({
        campaign_id: campaignId,
        save_id: saveId,
        command_id: generateCommandId(),
        expected_revision: state.revision,
      });
      setPendingCheck(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel check");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <section aria-label="Active Adventure">
        <p style={{ color: "var(--color-text-secondary)" }}>Loading realm state...</p>
      </section>
    );
  }

  if (error || !state) {
    return (
      <section aria-label="Active Adventure">
        <h1 style={{ color: "var(--color-danger)", marginBottom: "1rem" }}>Adventure Load Error</h1>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>{error}</p>
        <Link to="/" style={{ color: "var(--color-accent)" }}>
          ← Return to Library
        </Link>
      </section>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {narratorOffline && (
        <div
          role="status"
          aria-label="Narrator offline"
          style={{
            padding: "var(--space-3) var(--space-4)",
            backgroundColor: "rgba(251, 191, 36, 0.12)",
            border: "1px solid var(--color-warning)",
            borderRadius: "var(--radius-md)",
            color: "var(--color-warning)",
            fontSize: "var(--font-size-sm)",
          }}
        >
          Narrator offline — the local model is unavailable, so actions cannot be interpreted
          right now. The game state is safe; try again once Ollama is running.
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 340px",
          gap: "2rem",
          alignItems: "flex-start",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <NarrativeLog entries={entries} />

          {pendingCheck && (
            <CheckPanel
              check={pendingCheck}
              submitting={submitting}
              onResolve={handleResolveCheck}
              onCancel={handleCancelCheck}
            />
          )}

          {!pendingCheck && (
            <ActionComposer
              disabled={submitting}
              submitting={submitting}
              onSubmit={handleTakeAction}
            />
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <ContextRail
            save={state}
            encounters={encounters}
            engaging={engaging}
            onEngage={handleEngage}
          />
          {campaignId && saveId && (
            // Keyed on revision so a committed action re-reads progression (XP, HP, tokens).
            <CharacterPanel key={state.revision} campaignId={campaignId} saveId={saveId} />
          )}
          <RollHistory history={rollHistory} />
        </div>
      </div>
    </div>
  );
}
