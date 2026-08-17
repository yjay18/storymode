import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RuntimeStateResponse } from "../../api/schema";
import { InventoryPanel } from "./InventoryPanel";

describe("InventoryPanel", () => {
  it("renders empty message when inventory is empty", () => {
    const mockState: RuntimeStateResponse = {
      save_id: "save-1",
      campaign_id: "world-1",
      revision: 1,
      player: {
        name: "Aria",
        level: 1,
        hp: 10,
        max_hp: 10,
        mana: 5,
        max_mana: 5,
        attributes: {},
        equipped_skills: [],
        inventory: [],
      },
      current_area_id: "start",
      in_combat: false,
    };

    render(<InventoryPanel runtimeState={mockState} />);
    expect(screen.getByText(/Your inventory is empty/i)).toBeInTheDocument();
  });

  it("renders list of items with quantities", () => {
    const mockState: RuntimeStateResponse = {
      save_id: "save-1",
      campaign_id: "world-1",
      revision: 1,
      player: {
        name: "Aria",
        level: 1,
        hp: 10,
        max_hp: 10,
        mana: 5,
        max_mana: 5,
        attributes: {},
        equipped_skills: [],
        inventory: [
          { item_id: "health_potion", quantity: 3 },
          { item_id: "iron_dagger", quantity: 1 },
        ],
      },
      current_area_id: "start",
      in_combat: false,
    };

    render(<InventoryPanel runtimeState={mockState} />);
    expect(screen.getByText("health_potion")).toBeInTheDocument();
    expect(screen.getByText("x3")).toBeInTheDocument();
    expect(screen.getByText("iron_dagger")).toBeInTheDocument();
    expect(screen.getByText("x1")).toBeInTheDocument();
  });
});
