import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CombatCommandBar } from "./CombatCommandBar";

describe("CombatCommandBar", () => {
  it("renders skills, defend, flee, and triggers commands", () => {
    const onExecuteCommand = vi.fn();

    render(
      <CombatCommandBar
        availableSkills={["shadow_strike"]}
        canFlee={true}
        canYield={false}
        isPlayerTurn={true}
        submitting={false}
        selectedTargetId="goblin_1"
        onExecuteCommand={onExecuteCommand}
      />,
    );

    expect(screen.getByRole("button", { name: /Use shadow_strike/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Defend/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Attempt Flee/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Use shadow_strike/i }));
    expect(onExecuteCommand).toHaveBeenCalledWith("skill", "shadow_strike");

    fireEvent.click(screen.getByRole("button", { name: /Defend/i }));
    expect(onExecuteCommand).toHaveBeenCalledWith("defend");
  });
});
