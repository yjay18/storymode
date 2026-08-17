import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { RecoveryScreen } from "./RecoveryScreen";

describe("RecoveryScreen", () => {
  it("renders save diagnosis input and shows available snapshots", async () => {
    render(
      <MemoryRouter>
        <RecoveryScreen />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /Save Recovery/i })).toBeInTheDocument();
    const input = screen.getByLabelText(/Save Slot Identifier/i);
    expect(input).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "corrupted_slot_1" } });
    fireEvent.click(screen.getByRole("button", { name: /Diagnose Save/i }));

    await waitFor(() => {
      expect(screen.getByText("Available Validated Snapshots")).toBeInTheDocument();
      expect(screen.getByText("Snapshot Rev 3")).toBeInTheDocument();
    });
  });
});
