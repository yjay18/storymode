import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

function Bomb(): React.JSX.Element {
  throw new Error("KABOOM");
}

describe("ErrorBoundary", () => {
  it("catches render errors and displays fallback UI", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>,
    );

    expect(screen.getByRole("main", { name: "Application Error" })).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("KABOOM")).toBeInTheDocument();

    consoleError.mockRestore();
  });
});
