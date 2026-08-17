import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RollHistory, RollHistoryItem } from "./RollHistory";

describe("RollHistory", () => {
  it("renders empty message when history is empty", () => {
    render(<RollHistory history={[]} />);
    expect(screen.getByText("No dice rolls recorded yet.")).toBeInTheDocument();
  });

  it("renders roll items with trait, DC, and outcome", () => {
    const history: RollHistoryItem[] = [
      {
        id: "roll-1",
        checkId: "chk-1",
        trait: "brawn",
        dc: 12,
        outcome: "Passed",
        timestamp: "12:00:00 PM",
      },
    ];

    render(<RollHistory history={history} />);
    expect(screen.getByText("Recent Rolls")).toBeInTheDocument();
    expect(screen.getByText("brawn")).toBeInTheDocument();
    expect(screen.getByText("(DC 12)")).toBeInTheDocument();
    expect(screen.getByText("Passed")).toBeInTheDocument();
  });
});
