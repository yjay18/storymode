import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PlayerProgressionView } from "../../api/schema";
import { InventoryPanel } from "./InventoryPanel";

function makePlayer(inventory: PlayerProgressionView["inventory"]): PlayerProgressionView {
  return {
    id: "player-1",
    name: "Aria",
    level: 1,
    xp: 0,
    upgrade_tokens: 0,
    hp_current: 10,
    hp_maximum: 10,
    mana_current: 5,
    mana_maximum: 5,
    combat_loadout: [],
    known_skills: [],
    inventory,
  };
}

describe("InventoryPanel", () => {
  it("renders empty message when inventory is empty", () => {
    render(<InventoryPanel player={makePlayer([])} />);
    expect(screen.getByText(/Your inventory is empty/i)).toBeInTheDocument();
  });

  it("renders list of items with quantities", () => {
    render(
      <InventoryPanel
        player={makePlayer([
          { item_id: "health_potion", quantity: 3 },
          { item_id: "iron_dagger", quantity: 1 },
        ])}
      />,
    );
    expect(screen.getByText("health_potion")).toBeInTheDocument();
    expect(screen.getByText("x3")).toBeInTheDocument();
    expect(screen.getByText("iron_dagger")).toBeInTheDocument();
    expect(screen.getByText("x1")).toBeInTheDocument();
  });
});
