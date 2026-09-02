import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type { CombatParticipant, CombatViewResponse } from "../../api/schema";
import { CombatScreen } from "./CombatScreen";

function participant(side: CombatParticipant["side"], hp: number): CombatParticipant {
  return {
    hp: { current: hp, maximum: hp },
    armour: { current: 0, maximum: 0 },
    mana: { current: 10, maximum: 10 },
    statuses: [],
    known_combat_skills: [],
    combat_loadout: [],
    side,
  };
}

describe("CombatScreen", () => {
  it("loads the combat view and renders enemies, turn order, and allowed actions", async () => {
    const mockView: CombatViewResponse = {
      save_id: "s1",
      campaign_id: "w1",
      revision: 5,
      combat: {
        encounter_id: "encounter-1",
        phase: "active",
        round: 1,
        order: ["player-1", "orc_berserker"],
        current_index: 0,
        participants: {
          "player-1": participant("party", 20),
          orc_berserker: participant("enemy", 24),
        },
        tie_break_records: [],
        encounter_modifiers: [],
        origin_ids: [],
      },
      allowed_actions: [
        {
          action_kind: "use_skill",
          skill_id: "whirlwind",
          skill_name: "Whirlwind",
          mana_cost: 2,
          target_rule: "single_enemy",
          valid_target_ids: ["orc_berserker"],
        },
      ],
    };

    vi.spyOn(defaultApiClient, "getCombatView").mockResolvedValue(mockView);

    render(
      <MemoryRouter initialEntries={["/play/w1/s1/combat/combat-enc-1"]}>
        <Routes>
          <Route path="/play/:campaignId/:saveId/combat/:combatId" element={<CombatScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Entering tactical encounter...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Tactical Encounter/i })).toBeInTheDocument();
      expect(screen.getAllByText("orc_berserker").length).toBeGreaterThan(0);
      expect(screen.getByText("ROUND 1")).toBeInTheDocument();
      expect(screen.getByText("★ Your Turn")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Use whirlwind/i })).toBeInTheDocument();
    });
  });
});
