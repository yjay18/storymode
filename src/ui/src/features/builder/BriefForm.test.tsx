import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type { DraftState } from "../../api/schema";
import { BriefForm } from "./BriefForm";

describe("BriefForm", () => {
  it("renders all guided brief inputs and submits to API", async () => {
    const mockDraft: DraftState = {
      draft_id: "draft-guided-123",
      revision: 1,
      brief: {
        title: "The Silver Spire",
        premise: "A tower reaching the stars.",
      },
      stages: {} as DraftState["stages"],
      diagnostics: [],
      is_published: false,
    };

    const createSpy = vi
      .spyOn(defaultApiClient, "createGuidedDraft")
      .mockResolvedValue(mockDraft);

    render(
      <MemoryRouter>
        <BriefForm />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Guided Campaign Builder" })).toBeInTheDocument();
    expect(screen.getByLabelText(/Campaign Title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/World Premise & Lore/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Campaign Title/i), {
      target: { value: "The Silver Spire" },
    });
    fireEvent.change(screen.getByLabelText(/World Premise & Lore/i), {
      target: { value: "A tower reaching the stars." },
    });

    fireEvent.click(screen.getByRole("button", { name: /Initialize Campaign Draft/i }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "The Silver Spire",
          premise: "A tower reaching the stars.",
        }),
      );
    });
  });
});
