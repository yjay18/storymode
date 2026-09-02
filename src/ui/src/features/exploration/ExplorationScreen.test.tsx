import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import { ApiHttpError } from "../../api/errors";
import type {
  PendingCheck,
  ResolveCheckResponse,
  SaveSummaryResponse,
  SubmitActionResponse,
} from "../../api/schema";
import { ExplorationScreen } from "./ExplorationScreen";

const baseSave: SaveSummaryResponse = {
  save_id: "save-1",
  campaign_id: "world-1",
  revision: 1,
  player_name: "Eldrin",
  difficulty: "normal",
  current_area_id: "forgotten_library",
  slot_name: "Main",
  slot_kind: "manual",
};

const pendingCheck: PendingCheck = {
  check_id: "chk-1",
  source_command_id: "cmd-1",
  source_revision: 2,
  original_input: "pick the lock",
  resolved_operation: "pick the lock",
  actor_id: "player-1",
  target_ids: ["lockbox"],
  stat: "dexterity",
  skill_id: null,
  named_modifiers: { Tools: 2 },
  semantic_difficulty: "standard",
  base_dc: 12,
  difficulty_adjustment: 2,
  final_dc: 14,
  stakes: "The alarm may sound.",
  allowed_outcomes: { natural_1: [], low: [], standard: [], strong: [], natural_20: [] },
};

function mockNoCombatAndCampaign() {
  vi.spyOn(defaultApiClient, "getCombatView").mockResolvedValue({
    save_id: "save-1",
    campaign_id: "world-1",
    revision: 1,
    combat: null,
    allowed_actions: [],
  });
  vi.spyOn(defaultApiClient, "getCampaign").mockResolvedValue({
    campaign_id: "world-1",
    title: "World",
    description: "",
    version: "1.0.0",
    status: "published",
    campaign_length: "medium",
    backgrounds: [],
    areas: [],
    area_count: 0,
    has_valid_point_buy: true,
  });
}

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={["/play/world-1/save-1"]}>
      <Routes>
        <Route path="/play/:campaignId/:saveId" element={<ExplorationScreen />} />
        <Route path="/play/:campaignId/:saveId/combat" element={<div>Combat Route</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ExplorationScreen", () => {
  it("runs a look -> pending check -> resolve flow with narration and roll breakdown", async () => {
    const checkResp: SubmitActionResponse = {
      save_id: "save-1",
      campaign_id: "world-1",
      revision: 2,
      has_pending_check: true,
      pending_check: pendingCheck,
    };
    const resolveResp: ResolveCheckResponse = {
      save_id: "save-1",
      campaign_id: "world-1",
      revision: 3,
      roll: 17,
      band: "strong",
      narration: "The lock yields with a soft click.",
    };

    mockNoCombatAndCampaign();
    const getSaveSpy = vi.spyOn(defaultApiClient, "getSave");
    getSaveSpy.mockResolvedValueOnce(baseSave); // initial load (rev 1)
    getSaveSpy.mockResolvedValue({ ...baseSave, revision: 2 }); // refreshes after submit
    vi.spyOn(defaultApiClient, "submitAction").mockResolvedValue(checkResp);
    const resolveSpy = vi
      .spyOn(defaultApiClient, "resolveCheck")
      .mockResolvedValue(resolveResp);

    renderScreen();

    await waitFor(() => expect(screen.getByText("Eldrin")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/What do you want to do\?/i), {
      target: { value: "pick the lock" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Take Action/i }));

    await waitFor(() => expect(screen.getByText("DC 14")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Roll d20 Check/i }));

    await waitFor(() => {
      expect(resolveSpy).toHaveBeenCalledWith(
        expect.objectContaining({ expected_revision: 2, use_luck: false }),
      );
      // Roll breakdown labels: die, modifiers, total, DC, outcome.
      expect(screen.getByText("Die")).toBeInTheDocument();
      expect(screen.getByText("Modifiers")).toBeInTheDocument();
      expect(screen.getByText("Total")).toBeInTheDocument();
      expect(screen.getByText("DC")).toBeInTheDocument();
      expect(screen.getByText("Outcome")).toBeInTheDocument();
      expect(screen.getByText("Tools +2")).toBeInTheDocument();
      expect(screen.getAllByText("17").length).toBeGreaterThan(0);
      expect(screen.getByText('"The lock yields with a soft click."')).toBeInTheDocument();
    });
  });

  it("shows the narrator-offline banner on a 503 and keeps the composer usable", async () => {
    mockNoCombatAndCampaign();
    vi.spyOn(defaultApiClient, "getSave").mockResolvedValue(baseSave);
    vi.spyOn(defaultApiClient, "submitAction").mockRejectedValue(
      new ApiHttpError(503, "interpreter_not_configured", "Action interpreter unavailable"),
    );

    renderScreen();

    await waitFor(() => expect(screen.getByText("Eldrin")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/What do you want to do\?/i), {
      target: { value: "look around" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Take Action/i }));

    await waitFor(() => {
      expect(screen.getByLabelText("Narrator offline")).toBeInTheDocument();
    });
    // Composer remains available.
    expect(screen.getByLabelText(/What do you want to do\?/i)).toBeInTheDocument();
  });
});
