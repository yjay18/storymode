import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RuntimeStateResponse } from "../../api/schema";
import { ContextRail } from "./ContextRail";

describe("ContextRail", () => {
  it("renders player stats, HP, Mana, and current area", () => {
    const mockState: RuntimeStateResponse = {
      save_id: "save-1",
      campaign_id: "iron-citadel",
      revision: 4,
      player: {
        name: "Valerius",
        level: 2,
        hp: 18,
        max_hp: 20,
        mana: 8,
        max_mana: 10,
        attributes: {
          brawn: 3,
          finesse: 2,
        },
        equipped_skills: ["strike", "parry"],
        inventory: [],
      },
      current_area_id: "castle_courtyard",
      in_combat: false,
    };

    render(<ContextRail runtimeState={mockState} />);

    expect(screen.getByText("Valerius")).toBeInTheDocument();
    expect(screen.getByText("Lvl 2")).toBeInTheDocument();
    expect(screen.getByText("18 / 20")).toBeInTheDocument();
    expect(screen.getByText("8 / 10")).toBeInTheDocument();
    expect(screen.getByText("castle_courtyard")).toBeInTheDocument();
    expect(screen.getByText("brawn")).toBeInTheDocument();
  });
});
