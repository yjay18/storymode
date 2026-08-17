import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { CampaignSummary } from "../../api/schema";
import { CampaignList } from "./CampaignList";

describe("CampaignList", () => {
  it("renders empty state with create campaign links", () => {
    render(
      <MemoryRouter>
        <CampaignList campaigns={[]} loading={false} error={null} onRetry={vi.fn()} />
      </MemoryRouter>,
    );
    expect(screen.getByText("No Campaigns Found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Guided Builder" })).toBeInTheDocument();
  });

  it("renders campaign cards when campaigns are available", () => {
    const campaigns: CampaignSummary[] = [
      {
        campaign_id: "iron-citadel",
        campaign_version: "1.0.0",
        title: "The Iron Citadel",
        theme: "Dark fantasy siege and political survival",
        source_type: "novel",
        source_summary: "A fallen empire.",
        default_difficulty: "normal",
        campaign_length: "medium",
        status: "published",
        created_at: "2026-08-17T00:00:00Z",
      },
    ];

    render(
      <MemoryRouter>
        <CampaignList campaigns={campaigns} loading={false} error={null} onRetry={vi.fn()} />
      </MemoryRouter>,
    );

    expect(screen.getByText("The Iron Citadel")).toBeInTheDocument();
    expect(screen.getByText("Dark fantasy siege and political survival")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View Details →" })).toBeInTheDocument();
  });
});
