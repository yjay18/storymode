import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type { CampaignSummary, SaveSlotSummary } from "../../api/schema";
import { CampaignDetail } from "./CampaignDetail";

describe("CampaignDetail", () => {
  it("fetches and renders campaign details and saves", async () => {
    const mockCamp: CampaignSummary = {
      campaign_id: "test-world",
      campaign_version: "1.0.0",
      title: "Test World of Legends",
      theme: "Heroic fantasy and exploration",
      source_type: "prompt",
      source_summary: "A boundless world.",
      default_difficulty: "normal",
      campaign_length: "medium",
      status: "published",
      created_at: "2026-08-17T00:00:00Z",
    };

    const mockSaves: SaveSlotSummary[] = [
      {
        save_id: "save-hero-1",
        campaign_id: "test-world",
        campaign_fingerprint: "abc123",
        slot_number: 1,
        player_name: "Sir Lancelot",
        current_area_id: "castle_courtyard",
        in_combat: false,
        revision: 2,
        created_at: "2026-08-17T00:00:00Z",
        updated_at: "2026-08-17T00:00:00Z",
      },
    ];

    vi.spyOn(defaultApiClient, "getCampaign").mockResolvedValue(mockCamp);
    vi.spyOn(defaultApiClient, "listSaves").mockResolvedValue(mockSaves);

    render(
      <MemoryRouter initialEntries={["/campaigns/test-world"]}>
        <Routes>
          <Route path="/campaigns/:campaignId" element={<CampaignDetail />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Loading campaign details...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Test World of Legends" })).toBeInTheDocument();
      expect(screen.getByText("Sir Lancelot")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Continue →" })).toBeInTheDocument();
    });
  });
});
