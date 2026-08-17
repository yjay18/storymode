import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type { DraftStage, DraftStageState, DraftState } from "../../api/schema";
import { DraftWorkspace } from "./DraftWorkspace";

describe("DraftWorkspace", () => {
  it("loads and displays draft progress and premise", async () => {
    const mockDraft: DraftState = {
      draft_id: "draft-ws-1",
      revision: 3,
      brief: {
        title: "The Whispering Woods",
        premise: "A forest where the trees speak ancient forgotten secrets.",
      },
      stages: {
        meta_style: {
          stage: "meta_style",
          status: "valid",
          attempts: 1,
          diagnostics: [],
        },
      } as unknown as Record<DraftStage, DraftStageState>,
      diagnostics: [],
      is_published: false,
    };

    vi.spyOn(defaultApiClient, "getDraft").mockResolvedValue(mockDraft);

    render(
      <MemoryRouter initialEntries={["/builder/drafts/draft-ws-1"]}>
        <Routes>
          <Route path="/builder/drafts/:draftId" element={<DraftWorkspace />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Loading campaign draft...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "The Whispering Woods" })).toBeInTheDocument();
      expect(screen.getByText(/A forest where the trees speak/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Publish Campaign Pack/i })).toBeInTheDocument();
    });
  });
});
