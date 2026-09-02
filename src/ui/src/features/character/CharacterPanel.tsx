import React, { useEffect, useState } from "react";
import { defaultApiClient } from "../../api/client";
import { generateCommandId } from "../../api/commands";
import { ApiClientError } from "../../api/errors";
import type { ProgressionViewResponse } from "../../api/schema";

interface CharacterPanelProps {
  campaignId: string;
  saveId: string;
  /** Loadout edits are locked during combat (docs/ux/combat-ui.md mode guards). */
  inCombat?: boolean;
}

export function CharacterPanel({
  campaignId,
  saveId,
  inCombat = false,
}: CharacterPanelProps): React.JSX.Element {
  const [view, setView] = useState<ProgressionViewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<boolean>(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        setView(await defaultApiClient.getProgression(campaignId, saveId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load progression");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [campaignId, saveId]);

  const runMutation = async (op: (revision: number) => Promise<ProgressionViewResponse>) => {
    if (!view) return;
    setBusy(true);
    setActionError(null);
    try {
      const resp = await op(view.revision);
      setView({ save_id: resp.save_id, revision: resp.revision, player: resp.player });
    } catch (err) {
      // The server owns the rule; render its typed message verbatim.
      setActionError(err instanceof ApiClientError ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  const handleUpgrade = (skillId: string) =>
    runMutation((revision) =>
      defaultApiClient.upgradeSkill(campaignId, saveId, {
        command_id: generateCommandId(),
        expected_revision: revision,
        skill_id: skillId,
      }),
    );

  const handleToggleLoadout = (skillId: string) => {
    if (!view) return;
    const current = view.player.combat_loadout;
    const loadout = current.includes(skillId)
      ? current.filter((id) => id !== skillId)
      : [...current, skillId];
    return runMutation((revision) =>
      defaultApiClient.setLoadout(campaignId, saveId, {
        command_id: generateCommandId(),
        expected_revision: revision,
        loadout,
      }),
    );
  };

  if (loading) {
    return (
      <section aria-label="Character Sheet">
        <p style={{ color: "var(--color-text-secondary)" }}>Loading character...</p>
      </section>
    );
  }

  if (error || !view) {
    return (
      <section aria-label="Character Sheet">
        <p style={{ color: "var(--color-danger)" }}>{error}</p>
      </section>
    );
  }

  const player = view.player;
  const slots = [0, 1, 2, 3].map((i) => player.combat_loadout[i] ?? null);

  return (
    <section
      aria-label="Character Sheet"
      style={{
        padding: "var(--space-4)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div style={{ marginBottom: "1rem" }}>
        <h2 style={{ fontSize: "var(--font-size-xl)" }}>{player.name}</h2>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
          Level {player.level} • {player.xp} XP •{" "}
          <span aria-label="Upgrade tokens">
            {player.upgrade_tokens} token{player.upgrade_tokens === 1 ? "" : "s"}
          </span>
        </p>
        <p style={{ fontSize: "var(--font-size-sm)", marginTop: "0.25rem" }}>
          HP {player.hp_current}/{player.hp_maximum} • Mana {player.mana_current}/
          {player.mana_maximum}
        </p>
      </div>

      {actionError && (
        <p
          role="alert"
          style={{
            color: "var(--color-danger)",
            fontSize: "var(--font-size-xs)",
            marginBottom: "0.75rem",
          }}
        >
          {actionError}
        </p>
      )}

      <div style={{ marginBottom: "1rem" }}>
        <h3 style={sectionHeading}>Loadout (4 slots)</h3>
        <ol style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "var(--font-size-sm)" }}>
          {slots.map((slot, i) => (
            <li key={i}>{slot ?? <em style={{ color: "var(--color-text-muted)" }}>empty</em>}</li>
          ))}
        </ol>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <h3 style={sectionHeading}>Known Skills ({player.known_skills.length})</h3>
        {player.known_skills.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
            No skills learned yet.
          </p>
        ) : (
          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {player.known_skills.map((skill) => {
              const equipped = player.combat_loadout.includes(skill.skill_id);
              return (
                <li
                  key={skill.skill_id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "0.5rem",
                    padding: "var(--space-2) var(--space-3)",
                    backgroundColor: "var(--color-bg-elevated)",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "var(--font-size-sm)",
                  }}
                >
                  <span>
                    {skill.skill_id} (Lv {skill.current_level})
                  </span>
                  <span style={{ display: "flex", gap: "0.5rem" }}>
                    <button type="button" disabled={busy} onClick={() => handleUpgrade(skill.skill_id)}>
                      Upgrade
                    </button>
                    <button
                      type="button"
                      disabled={busy || inCombat}
                      onClick={() => handleToggleLoadout(skill.skill_id)}
                    >
                      {equipped ? "Unequip" : "Equip"}
                    </button>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div>
        <h3 style={sectionHeading}>Fusion</h3>
        <p style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
          No eligible fusion recipes. {/* read-only until recipe data is served */}
        </p>
      </div>
    </section>
  );
}

const sectionHeading: React.CSSProperties = {
  fontSize: "var(--font-size-sm)",
  textTransform: "uppercase",
  color: "var(--color-text-muted)",
  marginBottom: "0.5rem",
};
