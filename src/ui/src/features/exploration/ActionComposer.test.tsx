import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ActionComposer } from "./ActionComposer";

describe("ActionComposer", () => {
  it("submits action text and enforces character limit", () => {
    const onSubmit = vi.fn();
    render(<ActionComposer disabled={false} submitting={false} onSubmit={onSubmit} />);

    const input = screen.getByLabelText(/What do you want to do\?/i);
    expect(input).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "Examine the glowing runes" } });
    fireEvent.click(screen.getByRole("button", { name: /Take Action/i }));

    expect(onSubmit).toHaveBeenCalledWith("Examine the glowing runes");
  });

  it("disables submit button when input is empty or submitting", () => {
    const onSubmit = vi.fn();
    render(<ActionComposer disabled={true} submitting={false} onSubmit={onSubmit} />);

    const btn = screen.getByRole("button", { name: /Take Action/i });
    expect(btn).toBeDisabled();
  });
});
