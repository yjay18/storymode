import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import { ApiValidationError } from "../../api/errors";
import type {
  FusionRecipeView,
  PlayerProgressionView,
  ProgressionViewResponse,
} from "../../api/schema";
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

function mockFusion(recipes: FusionRecipeView[] = []) {
  return vi
    .spyOn(defaultApiClient, "listFusionRecipes")
    .mockResolvedValue({ save_id: "s1", revision: 1, recipes });
}

const eligible: FusionRecipeView = {
  recipe_id: "r-ready",
  source_skill_ids: ["slash", "fireball"],
  result_skill_id: "flame_strike",
  catalyst_item_id: "fire_gem",
  catalyst_quantity: 2,
  blocked_reason: null,
};

const blocked: FusionRecipeView = {
  recipe_id: "r-blocked",
  source_skill_ids: ["guard", "shout"],
  result_skill_id: "bulwark",
  catalyst_item_id: "iron_core",
  catalyst_quantity: 1,
  blocked_reason: "Protagonist does not know source skill guard",
};

describe("CharacterPanel", () => {
  it("upgrades a skill: token count decrements and skill level increments", async () => {
    vi.spyOn(defaultApiClient, "getProgression").mockResolvedValue(initialView);
    mockFusion();
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
    mockFusion();
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
    mockFusion();

    render(<CharacterPanel campaignId="w1" saveId="s1" />);

    await waitFor(() => expect(screen.getByText(/120 XP/)).toBeInTheDocument());
    // No "120 / N XP" progress form when the server carries no threshold.
    expect(screen.queryByText(/120 \/ /)).not.toBeInTheDocument();
  });

  it("lists served fusion recipes, eligible first, with the server's reason", async () => {
    vi.spyOn(defaultApiClient, "getProgression").mockResolvedValue(initialView);
    mockFusion([blocked, eligible]);

    render(<CharacterPanel campaignId="w1" saveId="s1" />);

    await waitFor(() => expect(screen.getByText("slash + fireball → flame_strike")).toBeInTheDocument());
    expect(screen.getByText("Ready — needs 2 fire_gem")).toBeInTheDocument();
    expect(
      screen.getByText("Protagonist does not know source skill guard"),
    ).toBeInTheDocument();

    // The eligible recipe is ordered ahead of the blocked one.
    const rendered = screen.getAllByRole("listitem").map((li) => li.textContent ?? "");
    const readyAt = rendered.findIndex((t) => t.includes("flame_strike"));
    const blockedAt = rendered.findIndex((t) => t.includes("bulwark"));
    expect(readyAt).toBeLessThan(blockedAt);
  });

  it("says so when the campaign authors no fusion recipes", async () => {
    vi.spyOn(defaultApiClient, "getProgression").mockResolvedValue(initialView);
    mockFusion([]);

    render(<CharacterPanel campaignId="w1" saveId="s1" />);

    await waitFor(() =>
      expect(screen.getByText("No fusion recipes in this campaign.")).toBeInTheDocument(),
    );
  });
});
