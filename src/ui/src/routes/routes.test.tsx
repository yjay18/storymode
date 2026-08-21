import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../api/client";
import { AppShell } from "../components/AppShell";
import { AppRoutes } from "./index";

describe("AppRoutes", () => {
  it("renders library route on /", async () => {
    vi.spyOn(defaultApiClient, "getHealth").mockResolvedValue({
      status: "ok",
      version: "1.0.0",
      ollama_reachable: true,
      model_text_available: true,
      model_image_available: false,
      models: [],
    });
    vi.spyOn(defaultApiClient, "listCampaigns").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Local System Readiness")).toBeInTheDocument();
      expect(screen.getByText("No Campaigns Found")).toBeInTheDocument();
    });
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

  it("renders book import dropzone on /builder/import", () => {
    render(
      <MemoryRouter initialEntries={["/builder/import"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: /Drop in an EPUB or Book/i })).toBeInTheDocument();
  });

  it("renders recovery route on /recovery", () => {
    render(
      <MemoryRouter initialEntries={["/recovery"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: /Save Recovery/i })).toBeInTheDocument();
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
