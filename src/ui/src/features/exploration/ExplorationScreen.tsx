import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import { createCommandTracker } from "../../api/commands";
import type { RuntimeStateResponse } from "../../api/schema";
import { ActionComposer } from "./ActionComposer";
import { CheckPanel, PendingCheckData } from "./CheckPanel";
import { ContextRail } from "./ContextRail";
import { LogEntry, NarrativeLog } from "./NarrativeLog";
import { RollHistory, RollHistoryItem } from "./RollHistory";

export function ExplorationScreen(): React.JSX.Element {
  const { campaignId, saveId } = useParams<{ campaignId: string; saveId: string }>();
  const navigate = useNavigate();

  const [state, setState] = useState<RuntimeStateResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [pendingCheck, setPendingCheck] = useState<PendingCheckData | null>(null);
  const [rollHistory, setRollHistory] = useState<RollHistoryItem[]>([]);

  const trackerRef = useRef(createCommandTracker());

  useEffect(() => {
    const loadState = async () => {
      if (!campaignId || !saveId) return;
      setLoading(true);
      setError(null);
      try {
        const runtimeState = await defaultApiClient.getSave(campaignId, saveId);
        setState(runtimeState);
        if (runtimeState.in_combat && runtimeState.active_combat_id) {
          navigate(`/play/${campaignId}/${saveId}/combat/${runtimeState.active_combat_id}`);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load adventure state");
      } finally {
        setLoading(false);
      }
    };

    loadState();
  }, [campaignId, saveId, navigate]);

  const handleTakeAction = async (rawInput: string) => {
    if (!campaignId || !saveId || !state) return;

    const intentKey = `action-${state.revision}-${rawInput}`;
    const commandId = trackerRef.current.getOrGenerate(intentKey);

    const actionLogId = `user-${Date.now()}`;
    setEntries((prev) => [
      ...prev,
      { id: actionLogId, type: "player_action", content: rawInput },
    ]);

    setSubmitting(true);
    try {
      const resp = await defaultApiClient.executeAction(campaignId, saveId, {
        command_id: commandId,
        raw_input: rawInput,
        expected_revision: state.revision,
      });

      if (resp.status === "check_required" && resp.pending_check) {
        setPendingCheck({
          check_id: resp.pending_check.check_id,
          skill_or_attribute: resp.pending_check.skill_or_attribute,
          dc: resp.pending_check.dc,
          stakes_description: resp.pending_check.stakes_description,
          allow_luck_reroll: resp.pending_check.allow_luck_reroll,
        });
      } else {
        setPendingCheck(null);
      }

      setEntries((prev) => [
        ...prev,
        {
          id: `res-${Date.now()}`,
          type: "result",
          content: resp.outcome_summary,
          status: resp.status,
          narration: resp.narration,
        },
      ]);

      trackerRef.current.consume(intentKey);

      const updated = await defaultApiClient.getSave(campaignId, saveId);
      setState(updated);

      if (updated.in_combat && updated.active_combat_id) {
        navigate(`/play/${campaignId}/${saveId}/combat/${updated.active_combat_id}`);
      }
    } catch (err) {
      setEntries((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          type: "result",
          content: "Action failed",
          status: "rejected",
          errorReason: err instanceof Error ? err.message : "Transport error",
        },
      ]);
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolveCheck = async (useLuck: boolean) => {
    if (!campaignId || !saveId || !state || !pendingCheck) return;

    const intentKey = `check-${state.revision}-${pendingCheck.check_id}-${useLuck}`;
    const commandId = trackerRef.current.getOrGenerate(intentKey);

    setSubmitting(true);
    try {
      const resp = await defaultApiClient.resolveCheck(
        campaignId,
        saveId,
        pendingCheck.check_id,
        {
          command_id: commandId,
          use_luck: useLuck,
          expected_revision: state.revision,
        },
      );

      setRollHistory((prev) => [
        ...prev,
        {
          id: `roll-${Date.now()}`,
          checkId: pendingCheck.check_id,
          trait: pendingCheck.skill_or_attribute,
          dc: pendingCheck.dc,
          outcome: resp.status === "success" ? "Passed" : "Failed",
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);

      setEntries((prev) => [
        ...prev,
        {
          id: `res-${Date.now()}`,
          type: "result",
          content: resp.outcome_summary,
          status: resp.status,
          narration: resp.narration,
        },
      ]);

      setPendingCheck(null);
      trackerRef.current.consume(intentKey);

      const updated = await defaultApiClient.getSave(campaignId, saveId);
      setState(updated);
    } catch (err) {
      setEntries((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          type: "result",
          content: "Check resolution failed",
          status: "rejected",
          errorReason: err instanceof Error ? err.message : "Transport error",
        },
      ]);
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
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 280px",
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
              onCancel={() => setPendingCheck(null)}
            />
          )}

          {!pendingCheck && (
            <ActionComposer
              disabled={submitting || state.in_combat}
              submitting={submitting}
              onSubmit={handleTakeAction}
            />
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <ContextRail runtimeState={state} />
          <RollHistory history={rollHistory} />
        </div>
      </div>
    </div>
  );
}
