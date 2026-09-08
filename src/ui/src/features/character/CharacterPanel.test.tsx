import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import { ApiValidationError } from "../../api/errors";
import type { PlayerProgressionView, ProgressionViewResponse } from "../../api/schema";
import { CharacterPanel } from "./CharacterPanel";

function player(
  level: number,
  tokens: number,
  skillLevel: number,
  xpForNextLevel: number | null = 200,
): PlayerProgressionView {
  return {
    id: "player-1",
    name: "Theron",
    level,
    xp: 120,
    xp_for_next_level: xpForNextLevel,
    upgrade_tokens: tokens,
    hp_current: 25,
    hp_maximum: 25,
    mana_current: 12,
    mana_maximum: 15,
    combat_loadout: [],
    known_skills: [{ skill_id: "heavy_cleave", current_level: skillLevel }],
    inventory: [],
  };
}

const initialView: ProgressionViewResponse = {
  save_id: "s1",
  revision: 1,
  player: player(3, 2, 2),
};

describe("CharacterPanel", () => {
  it("upgrades a skill: token count decrements and skill level increments", async () => {
    vi.spyOn(defaultApiClient, "getProgression").mockResolvedValue(initialView);
    const upgradeSpy = vi.spyOn(defaultApiClient, "upgradeSkill").mockResolvedValue({
      save_id: "s1",
      revision: 2,
      receipt: {
        command_id: "c1",
        committed_revision: 2,
        result_kind: "upgrade",
        safe_result_summary: "ok",
      },
      player: player(3, 1, 3),
    });

    render(<CharacterPanel campaignId="w1" saveId="s1" />);

    await waitFor(() => expect(screen.getByText("2 tokens")).toBeInTheDocument());
    expect(screen.getByText("heavy_cleave (Lv 2)")).toBeInTheDocument();
    expect(screen.getByText(/120 \/ 200 XP/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Upgrade" }));

    await waitFor(() => {
      expect(upgradeSpy).toHaveBeenCalledWith(
        "w1",
        "s1",
        expect.objectContaining({ skill_id: "heavy_cleave", expected_revision: 1 }),
      );
      expect(screen.getByText("1 token")).toBeInTheDocument();
      expect(screen.getByText("heavy_cleave (Lv 3)")).toBeInTheDocument();
    });
  });

  it("renders the server message on a typed rejection", async () => {
    vi.spyOn(defaultApiClient, "getProgression").mockResolvedValue(initialView);
    vi.spyOn(defaultApiClient, "upgradeSkill").mockRejectedValue(
      new ApiValidationError("insufficient upgrade tokens"),
    );

    render(<CharacterPanel campaignId="w1" saveId="s1" />);

    await waitFor(() => expect(screen.getByText("2 tokens")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Upgrade" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("insufficient upgrade tokens"),
    );
  });

  it("shows raw XP when the server reports no next-level threshold", async () => {
    vi.spyOn(defaultApiClient, "getProgression").mockResolvedValue({
      save_id: "s1",
      revision: 1,
      player: player(10, 0, 5, null),
    });

    render(<CharacterPanel campaignId="w1" saveId="s1" />);

    await waitFor(() => expect(screen.getByText(/120 XP/)).toBeInTheDocument());
    // No "120 / N XP" progress form when the server carries no threshold.
    expect(screen.queryByText(/120 \/ /)).not.toBeInTheDocument();
  });
});
