import React, { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import { createCommandTracker } from "../../api/commands";
import type { PendingCheck, SaveSummaryResponse } from "../../api/schema";
import { ActionComposer } from "./ActionComposer";
import { CheckPanel, PendingCheckData } from "./CheckPanel";
import { ContextRail } from "./ContextRail";
import { LogEntry, NarrativeLog } from "./NarrativeLog";
import { RollHistory, RollHistoryItem } from "./RollHistory";

function toCheckPanelData(check: PendingCheck): PendingCheckData {
  return {
    check_id: check.check_id,
    skill_or_attribute: check.stat ?? check.skill_id ?? check.semantic_difficulty,
    dc: check.final_dc,
    stakes_description: check.stakes,
    allow_luck_reroll: true,
  };
}

export function ExplorationScreen(): React.JSX.Element {
  const { campaignId, saveId } = useParams<{ campaignId: string; saveId: string }>();

  const [state, setState] = useState<SaveSummaryResponse | null>(null);
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
        setState(await defaultApiClient.getSave(campaignId, saveId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load adventure state");
      } finally {
        setLoading(false);
      }
    };

    loadState();
  }, [campaignId, saveId]);

  const handleTakeAction = async (playerText: string) => {
    if (!campaignId || !saveId || !state) return;

    const intentKey = `action-${state.revision}-${playerText}`;
    const commandId = trackerRef.current.getOrGenerate(intentKey);

    setEntries((prev) => [
      ...prev,
      { id: `user-${Date.now()}`, type: "player_action", content: playerText },
    ]);

    setSubmitting(true);
    try {
      const resp = await defaultApiClient.submitAction({
        campaign_id: campaignId,
        save_id: saveId,
        command_id: commandId,
        expected_revision: state.revision,
        player_text: playerText,
      });

      if (resp.rejection_reason) {
        setEntries((prev) => [
          ...prev,
          {
            id: `res-${Date.now()}`,
            type: "result",
            content: "Action rejected",
            status: "rejected",
            errorReason: resp.rejection_reason ?? undefined,
          },
        ]);
      } else if (resp.has_pending_check && resp.pending_check) {
        setPendingCheck(toCheckPanelData(resp.pending_check));
      } else {
        setEntries((prev) => [
          ...prev,
          {
            id: `res-${Date.now()}`,
            type: "result",
            content: "You take action.",
            status: "success",
            narration: resp.narration ?? undefined,
          },
        ]);
      }

      trackerRef.current.consume(intentKey);
      setState(await defaultApiClient.getSave(campaignId, saveId));
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
      const resp = await defaultApiClient.resolveCheck({
        campaign_id: campaignId,
        save_id: saveId,
        command_id: commandId,
        expected_revision: state.revision,
        use_luck: useLuck,
      });

      setRollHistory((prev) => [
        ...prev,
        {
          id: `roll-${Date.now()}`,
          checkId: pendingCheck.check_id,
          trait: pendingCheck.skill_or_attribute,
          dc: pendingCheck.dc,
          total: resp.roll,
          outcome: resp.band,
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);

      setEntries((prev) => [
        ...prev,
        {
          id: `res-${Date.now()}`,
          type: "result",
          content: `Rolled ${resp.roll} — ${resp.band}`,
          status: "success",
          narration: resp.narration ?? undefined,
        },
      ]);

      setPendingCheck(null);
      trackerRef.current.consume(intentKey);
      setState(await defaultApiClient.getSave(campaignId, saveId));
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

  const handleCancelCheck = async () => {
    if (!campaignId || !saveId || !state || !pendingCheck) return;
    const commandId = trackerRef.current.getOrGenerate(`cancel-${pendingCheck.check_id}`);
    setSubmitting(true);
    try {
      await defaultApiClient.cancelCheck({
        campaign_id: campaignId,
        save_id: saveId,
        command_id: commandId,
        expected_revision: state.revision,
      });
      setPendingCheck(null);
      setState(await defaultApiClient.getSave(campaignId, saveId));
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
          <ContextRail save={state} />
          <RollHistory history={rollHistory} />
        </div>
      </div>
    </div>
  );
}
