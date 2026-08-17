import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RuntimeStateResponse } from "../../api/schema";
import { CharacterPanel } from "./CharacterPanel";

describe("CharacterPanel", () => {
  it("renders player name, level, attributes, and equipped skills", () => {
    const mockState: RuntimeStateResponse = {
      save_id: "save-1",
      campaign_id: "iron-citadel",
      revision: 2,
      player: {
        name: "Theron",
        level: 3,
        hp: 25,
        max_hp: 25,
        mana: 12,
        max_mana: 15,
        attributes: {
          brawn: 4,
          resolve: 3,
        },
        equipped_skills: ["heavy_cleave"],
        inventory: [],
      },
      current_area_id: "training_grounds",
      in_combat: false,
    };

    render(<CharacterPanel runtimeState={mockState} />);

    expect(screen.getByRole("heading", { name: "Theron" })).toBeInTheDocument();
    expect(screen.getByText("Level 3 Hero")).toBeInTheDocument();
    expect(screen.getByText("25 / 25")).toBeInTheDocument();
    expect(screen.getByText("12 / 15")).toBeInTheDocument();
    expect(screen.getByText("brawn")).toBeInTheDocument();
    expect(screen.getByText("heavy_cleave")).toBeInTheDocument();
  });
});
