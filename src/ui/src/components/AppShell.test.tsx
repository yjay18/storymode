import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("renders header, skip link, main content, and footer", () => {
    render(
      <MemoryRouter>
        <AppShell activeCampaignId="test-camp" activeSaveId="save-1" activeRevision={3}>
          <p>Test Child Content</p>
        </AppShell>
      </MemoryRouter>,
    );

    expect(screen.getByText("Skip to main content")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "STORYMODE" })).toBeInTheDocument();
    expect(screen.getByText("Test Child Content")).toBeInTheDocument();
    expect(screen.getByText("Campaign:")).toBeInTheDocument();
    expect(screen.getByText("test-camp")).toBeInTheDocument();
    expect(screen.getByText("save-1")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
