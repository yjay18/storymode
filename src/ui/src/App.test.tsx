import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { defaultApiClient } from "./api/client";

describe("App setup", () => {
  it("renders the Storymode app shell and default Campaign Library screen", async () => {
    vi.spyOn(defaultApiClient, "getHealth").mockResolvedValue({
      status: "ok",
      version: "1.0.0",
      ollama_reachable: true,
      model_text_available: true,
      model_image_available: false,
      models: [],
    });
    vi.spyOn(defaultApiClient, "listCampaigns").mockResolvedValue([]);

    render(<App />);
    expect(screen.getByRole("link", { name: "STORYMODE" })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Local System Readiness")).toBeInTheDocument();
      expect(screen.getByText("No Campaigns Found")).toBeInTheDocument();
    });
  });
});
