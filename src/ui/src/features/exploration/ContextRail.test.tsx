import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SaveSummaryResponse } from "../../api/schema";
import { ContextRail } from "./ContextRail";

describe("ContextRail", () => {
  it("renders player name, difficulty, slot, and current area", () => {
    const mockSave: SaveSummaryResponse = {
      save_id: "save-1",
      campaign_id: "iron-citadel",
      revision: 4,
      player_name: "Valerius",
      difficulty: "normal",
      current_area_id: "castle_courtyard",
      slot_name: "Main",
      slot_kind: "manual",
    };

    render(<ContextRail save={mockSave} />);

    expect(screen.getByText("Valerius")).toBeInTheDocument();
    expect(screen.getByText("normal")).toBeInTheDocument();
    expect(screen.getByText("castle_courtyard")).toBeInTheDocument();
    expect(screen.getByText(/Main/)).toBeInTheDocument();
  });
});
