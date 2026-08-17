import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type { ActionResponse, RuntimeStateResponse } from "../../api/schema";
import { ExplorationScreen } from "./ExplorationScreen";

describe("ExplorationScreen", () => {
  it("loads runtime state and allows executing actions", async () => {
    const mockState: RuntimeStateResponse = {
      save_id: "save-exp-1",
      campaign_id: "world-1",
      revision: 1,
      player: {
        name: "Eldrin",
        level: 1,
        hp: 15,
        max_hp: 15,
        mana: 10,
        max_mana: 10,
        attributes: { wit: 3 },
        equipped_skills: [],
        inventory: [],
      },
      current_area_id: "forgotten_library",
      in_combat: false,
    };

    const mockActionResp: ActionResponse = {
      command_id: "cmd-123",
      status: "success",
      narration: "You dust off the ancient tome.",
      outcome_summary: "You found a forgotten map.",
      new_revision: 2,
    };

    vi.spyOn(defaultApiClient, "getSave").mockResolvedValue(mockState);
    const actionSpy = vi
      .spyOn(defaultApiClient, "executeAction")
      .mockResolvedValue(mockActionResp);

    render(
      <MemoryRouter initialEntries={["/play/world-1/save-exp-1"]}>
        <Routes>
          <Route path="/play/:campaignId/:saveId" element={<ExplorationScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Loading realm state...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Eldrin")).toBeInTheDocument();
      expect(screen.getByText("forgotten_library")).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/What do you want to do\?/i);
    fireEvent.change(input, { target: { value: "Read the dusty book on the table" } });
    fireEvent.click(screen.getByRole("button", { name: /Take Action/i }));

    await waitFor(() => {
      expect(actionSpy).toHaveBeenCalledWith(
        "world-1",
        "save-exp-1",
        expect.objectContaining({
          raw_input: "Read the dusty book on the table",
          expected_revision: 1,
        }),
      );
      expect(screen.getByText("You found a forgotten map.")).toBeInTheDocument();
      expect(screen.getByText('"You dust off the ancient tome."')).toBeInTheDocument();
    });
  });
});
