import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PlayerProgressionView } from "../../api/schema";
import { CharacterPanel } from "./CharacterPanel";

describe("CharacterPanel", () => {
  it("renders player name, level, resources, and known skills", () => {
    const player: PlayerProgressionView = {
      id: "player-1",
      name: "Theron",
      level: 3,
      xp: 120,
      upgrade_tokens: 2,
      hp_current: 25,
      hp_maximum: 25,
      mana_current: 12,
      mana_maximum: 15,
      combat_loadout: ["heavy_cleave"],
      known_skills: [{ skill_id: "heavy_cleave", current_level: 2 }],
      inventory: [],
    };

    render(<CharacterPanel player={player} />);

    expect(screen.getByRole("heading", { name: "Theron" })).toBeInTheDocument();
    expect(screen.getByText(/Level 3/)).toBeInTheDocument();
    expect(screen.getByText("25 / 25")).toBeInTheDocument();
    expect(screen.getByText("12 / 15")).toBeInTheDocument();
    expect(screen.getByText(/heavy_cleave/)).toBeInTheDocument();
    expect(screen.getByText("Equipped")).toBeInTheDocument();
  });
});
