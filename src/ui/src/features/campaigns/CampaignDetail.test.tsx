import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type { CampaignDetail as CampaignDetailData } from "../../api/schema";
import { CampaignDetail } from "./CampaignDetail";

describe("CampaignDetail", () => {
  it("fetches and renders campaign details and a new-hero action", async () => {
    const mockCamp: CampaignDetailData = {
      campaign_id: "test-world",
      title: "Test World of Legends",
      description: "A boundless world.",
      version: "1.0.0",
      status: "published",
      campaign_length: "medium",
      backgrounds: [
        {
          id: "scout",
          name: "Scout",
          description: "A wary traveller.",
          stat_bonus: "dexterity",
          stat_bonus_value: 1,
          starting_skill_ids: [],
          starting_item_ids: [],
          starting_fact_ids: [],
        },
      ],
      areas: [],
      area_count: 4,
      has_valid_point_buy: true,
    };

    vi.spyOn(defaultApiClient, "getCampaign").mockResolvedValue(mockCamp);

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
      expect(screen.getByText("A boundless world.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "+ New Hero" })).toBeInTheDocument();
    });
  });
});
