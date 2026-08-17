import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type { CombatStateResponse } from "../../api/schema";
import { CombatScreen } from "./CombatScreen";

describe("CombatScreen", () => {
  it("loads combat state and displays enemies and tactical actions", async () => {
    const mockCombat: CombatStateResponse = {
      combat_id: "combat-enc-1",
      round: 1,
      turn_order: ["player", "orc_berserker"],
      active_entity_id: "player",
      is_player_turn: true,
      enemies: [
        {
          enemy_id: "orc_berserker",
          name: "Orc Berserker",
          hp: 24,
          max_hp: 24,
          is_defeated: false,
        },
      ],
      available_skills: ["whirlwind"],
      can_flee: true,
      can_yield: false,
      is_finished: false,
    };

    vi.spyOn(defaultApiClient, "getCombatState").mockResolvedValue(mockCombat);

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
      expect(screen.getByText("Orc Berserker")).toBeInTheDocument();
      expect(screen.getByText("ROUND 1")).toBeInTheDocument();
      expect(screen.getByText("★ Your Turn")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Use whirlwind/i })).toBeInTheDocument();
    });
  });
});
