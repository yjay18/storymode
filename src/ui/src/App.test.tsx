import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App setup", () => {
  it("renders the Storymode app shell and default Campaign Library screen", () => {
    render(<App />);
    expect(screen.getByRole("link", { name: "STORYMODE" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Campaign Library" })).toBeInTheDocument();
  });
});
