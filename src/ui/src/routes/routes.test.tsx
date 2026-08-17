import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppShell } from "../components/AppShell";
import { AppRoutes } from "./index";

describe("AppRoutes", () => {
  it("renders library route on /", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "Campaign Library" })).toBeInTheDocument();
  });

  it("renders guided builder route on /builder/guided", () => {
    render(
      <MemoryRouter initialEntries={["/builder/guided"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "Guided Campaign Builder" })).toBeInTheDocument();
  });

  it("renders quick builder route on /builder/quick", () => {
    render(
      <MemoryRouter initialEntries={["/builder/quick"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "Quick Prompt Builder" })).toBeInTheDocument();
  });

  it("renders recovery route on /recovery", () => {
    render(
      <MemoryRouter initialEntries={["/recovery"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "Save Recovery" })).toBeInTheDocument();
  });

  it("renders 404 on unknown route", () => {
    render(
      <MemoryRouter initialEntries={["/some/unknown/path"]}>
        <AppShell>
          <AppRoutes />
        </AppShell>
      </MemoryRouter>,
    );
    expect(screen.getByText("404 — Page Not Found")).toBeInTheDocument();
  });
});
