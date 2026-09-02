import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PendingCheck } from "../../api/schema";
import { CheckPanel } from "./CheckPanel";

const emptyOutcomes = {
  natural_1: [],
  low: [],
  standard: [],
  strong: [],
  natural_20: [],
};

describe("CheckPanel", () => {
  it("renders DC breakdown, trait, modifiers, stakes, and triggers resolution", () => {
    const check: PendingCheck = {
      check_id: "chk-1",
      source_command_id: "cmd-1",
      source_revision: 2,
      original_input: "pick the lock",
      resolved_operation: "pick the lock",
      actor_id: "player-1",
      target_ids: ["lockbox"],
      stat: "dexterity",
      skill_id: null,
      named_modifiers: { Tools: 2 },
      semantic_difficulty: "standard",
      base_dc: 12,
      difficulty_adjustment: 2,
      final_dc: 14,
      stakes: "If you fail, the alarm bell tolls.",
      allowed_outcomes: emptyOutcomes,
    };

    const onResolve = vi.fn();
    const onCancel = vi.fn();

    render(
      <CheckPanel check={check} submitting={false} onResolve={onResolve} onCancel={onCancel} />,
    );

    expect(screen.getByText("DC 14")).toBeInTheDocument();
    expect(screen.getByText("dexterity")).toBeInTheDocument();
    expect(screen.getByText(/Tools \+2/)).toBeInTheDocument();
    expect(screen.getByText(/Base DC 12 \+2 = Final DC 14/)).toBeInTheDocument();
    expect(screen.getByText(/If you fail, the alarm bell tolls/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Roll d20 Check/i }));
    expect(onResolve).toHaveBeenCalledWith(false);

    fireEvent.click(screen.getByRole("button", { name: /Spend Luck & Roll/i }));
    expect(onResolve).toHaveBeenCalledWith(true);

    fireEvent.click(screen.getByRole("button", { name: /Cancel/i }));
    expect(onCancel).toHaveBeenCalled();
  });
});
