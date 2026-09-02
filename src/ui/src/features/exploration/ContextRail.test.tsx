import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { EncounterView, SaveSummaryResponse } from "../../api/schema";
import { ContextRail } from "./ContextRail";

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

describe("ContextRail", () => {
  it("renders player, area, and lets the player engage an encounter", () => {
    const encounters: EncounterView[] = [
      { id: "encounter-1", enemy_archetype_ids: ["orc"], condition: "on approach" },
    ];
    const onEngage = vi.fn();

    render(
      <ContextRail save={mockSave} encounters={encounters} engaging={false} onEngage={onEngage} />,
    );

    expect(screen.getByText("Valerius")).toBeInTheDocument();
    expect(screen.getByText("castle_courtyard")).toBeInTheDocument();
    expect(screen.getByText(/encounter-1/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Engage" }));
    expect(onEngage).toHaveBeenCalledWith("encounter-1");
  });

  it("shows a placeholder when there are no encounters", () => {
    render(<ContextRail save={mockSave} encounters={[]} engaging={false} onEngage={vi.fn()} />);
    expect(screen.getByText(/No combat encounters here/i)).toBeInTheDocument();
  });
});
