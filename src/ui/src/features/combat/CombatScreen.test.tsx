import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type {
  AllowedCombatAction,
  CombatParticipant,
  CombatResponse,
  CombatState,
  CombatViewResponse,
} from "../../api/schema";
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

function combatState(round: number): CombatState {
  return {
    encounter_id: "encounter-1",
    phase: "active",
    round,
    order: ["player-1", "orc_berserker"],
    current_index: 0,
    participants: {
      "player-1": participant("party", 20),
      orc_berserker: participant("enemy", 24),
    },
    tie_break_records: [],
    encounter_modifiers: [],
    origin_ids: [],
  };
}

const skillAction: AllowedCombatAction = {
  action_kind: "use_skill",
  skill_id: "whirlwind",
  skill_name: "Whirlwind",
  mana_cost: 2,
  target_rule: "single_enemy",
  valid_target_ids: ["orc_berserker"],
};
const defendAction: AllowedCombatAction = {
  action_kind: "defend",
  mana_cost: 0,
  valid_target_ids: [],
};
const yieldAction: AllowedCombatAction = {
  action_kind: "yield",
  mana_cost: 0,
  valid_target_ids: [],
};

function renderCombat() {
  return render(
    <MemoryRouter initialEntries={["/play/w1/s1/combat"]}>
      <Routes>
        <Route path="/play/:campaignId/:saveId/combat" element={<CombatScreen />} />
        <Route path="/play/:campaignId/:saveId" element={<div>Exploration</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CombatScreen", () => {
  it("runs start -> skill -> defend -> yield, posting the right bodies", async () => {
    const view: CombatViewResponse = {
      save_id: "s1",
      campaign_id: "w1",
      revision: 5,
      combat: combatState(1),
      allowed_actions: [skillAction, defendAction, yieldAction],
    };
    const afterSkill: CombatResponse = {
      save_id: "s1",
      campaign_id: "w1",
      revision: 6,
      combat: combatState(2),
      allowed_actions: [defendAction, yieldAction],
      is_terminal: false,
      outcome: null,
      logs: ["Whirlwind strikes the orc."],
    };
    const afterDefend: CombatResponse = {
      ...afterSkill,
      revision: 7,
      allowed_actions: [yieldAction],
      logs: ["You brace behind your guard."],
    };
    const afterYield: CombatResponse = {
      save_id: "s1",
      campaign_id: "w1",
      revision: 8,
      combat: null,
      allowed_actions: [],
      is_terminal: true,
      outcome: "Yielded",
      logs: ["You lower your weapon."],
    };

    vi.spyOn(defaultApiClient, "getCombatView").mockResolvedValue(view);
    const skillSpy = vi.spyOn(defaultApiClient, "useSkill").mockResolvedValue(afterSkill);
    const defendSpy = vi.spyOn(defaultApiClient, "defend").mockResolvedValue(afterDefend);
    const yieldSpy = vi.spyOn(defaultApiClient, "yieldCombat").mockResolvedValue(afterYield);

    renderCombat();

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /Tactical Encounter/i })).toBeInTheDocument(),
    );
    // No free-text exploration input in combat (mode guard).
    expect(screen.queryByLabelText(/What do you want to do\?/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Use whirlwind/i }));
    await waitFor(() =>
      expect(skillSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          skill_id: "whirlwind",
          target_ids: ["orc_berserker"],
          expected_revision: 5,
        }),
      ),
    );
    await waitFor(() => expect(screen.getByText("Whirlwind strikes the orc.")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Defend/i }));
    await waitFor(() =>
      expect(defendSpy).toHaveBeenCalledWith(expect.objectContaining({ expected_revision: 6 })),
    );

    fireEvent.click(screen.getByRole("button", { name: /Yield/i }));
    await waitFor(() =>
      expect(yieldSpy).toHaveBeenCalledWith(expect.objectContaining({ expected_revision: 7 })),
    );

    await waitFor(() => {
      expect(screen.getByText(/Combat Concluded/i)).toBeInTheDocument();
      expect(screen.getByText("Yielded")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Return to exploration/i })).toBeInTheDocument();
    });
  });
});
