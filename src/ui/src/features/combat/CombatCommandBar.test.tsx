import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { AllowedCombatAction } from "../../api/schema";
import { CombatCommandBar } from "./CombatCommandBar";

const skill: AllowedCombatAction = {
  action_kind: "use_skill",
  skill_id: "shadow_strike",
  skill_name: "Shadow Strike",
  mana_cost: 3,
  target_rule: "single_enemy",
  valid_target_ids: ["goblin_1"],
};
const defend: AllowedCombatAction = { action_kind: "defend", mana_cost: 0, valid_target_ids: [] };
const flee: AllowedCombatAction = { action_kind: "flee", mana_cost: 0, valid_target_ids: [] };

describe("CombatCommandBar", () => {
  it("renders only allowed actions and executes them", () => {
    const onExecute = vi.fn();

    render(
      <CombatCommandBar
        allowedActions={[skill, defend, flee]}
        isPlayerTurn={true}
        submitting={false}
        selectedTargetId="goblin_1"
        onExecute={onExecute}
      />,
    );

    expect(screen.getByRole("button", { name: /Use Shadow Strike/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Defend/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Flee/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Use Shadow Strike/i }));
    expect(onExecute).toHaveBeenCalledWith(skill);

    fireEvent.click(screen.getByRole("button", { name: /Defend/i }));
    expect(onExecute).toHaveBeenCalledWith(defend);
  });

  it("disables a targeted skill when no target is selected", () => {
    render(
      <CombatCommandBar
        allowedActions={[skill]}
        isPlayerTurn={true}
        submitting={false}
        selectedTargetId={null}
        onExecute={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /Use Shadow Strike/i })).toBeDisabled();
  });
});
