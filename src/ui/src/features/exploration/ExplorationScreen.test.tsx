import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type { SaveSummaryResponse, SubmitActionResponse } from "../../api/schema";
import { ExplorationScreen } from "./ExplorationScreen";

describe("ExplorationScreen", () => {
  it("loads save state and submits an action to the real pipeline", async () => {
    const mockState: SaveSummaryResponse = {
      save_id: "save-exp-1",
      campaign_id: "world-1",
      revision: 1,
      player_name: "Eldrin",
      difficulty: "normal",
      current_area_id: "forgotten_library",
      slot_name: "Main",
      slot_kind: "manual",
    };

    const mockActionResp: SubmitActionResponse = {
      save_id: "save-exp-1",
      campaign_id: "world-1",
      revision: 2,
      has_pending_check: false,
      narration: "You dust off the ancient tome.",
    };

    vi.spyOn(defaultApiClient, "getSave").mockResolvedValue(mockState);
    const actionSpy = vi.spyOn(defaultApiClient, "submitAction").mockResolvedValue(mockActionResp);

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
        expect.objectContaining({
          campaign_id: "world-1",
          save_id: "save-exp-1",
          player_text: "Read the dusty book on the table",
          expected_revision: 1,
        }),
      );
      expect(screen.getByText('"You dust off the ancient tome."')).toBeInTheDocument();
    });
  });
});
