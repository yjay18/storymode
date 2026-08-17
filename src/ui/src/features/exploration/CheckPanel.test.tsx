import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CheckPanel, PendingCheckData } from "./CheckPanel";

describe("CheckPanel", () => {
  it("renders DC, trait, stakes, and triggers roll resolution", () => {
    const check: PendingCheckData = {
      check_id: "chk-1",
      skill_or_attribute: "finesse",
      dc: 14,
      stakes_description: "If you fail, the alarm bell tolls.",
      allow_luck_reroll: true,
    };

    const onResolve = vi.fn();
    const onCancel = vi.fn();

    render(
      <CheckPanel
        check={check}
        submitting={false}
        onResolve={onResolve}
        onCancel={onCancel}
      />,
    );

    expect(screen.getByText("DC 14")).toBeInTheDocument();
    expect(screen.getByText("finesse")).toBeInTheDocument();
    expect(screen.getByText(/If you fail, the alarm bell tolls/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Roll d20 Check/i }));
    expect(onResolve).toHaveBeenCalledWith(false);

    fireEvent.click(screen.getByRole("button", { name: /Spend Luck & Roll/i }));
    expect(onResolve).toHaveBeenCalledWith(true);

    fireEvent.click(screen.getByRole("button", { name: /Cancel/i }));
    expect(onCancel).toHaveBeenCalled();
  });
});
