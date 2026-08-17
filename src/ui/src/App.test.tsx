import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App setup", () => {
  it("renders the Storymode setup landmark and heading", () => {
    render(<App />);
    const landmark = screen.getByRole("main", { name: "Storymode setup" });
    expect(landmark).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Storymode setup",
    );
  });
});
