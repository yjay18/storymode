import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type { DraftState } from "../../api/schema";
import { QuickPromptForm } from "./QuickPromptForm";

describe("QuickPromptForm", () => {
  it("renders quick premise textarea and creates draft", async () => {
    const mockDraft: DraftState = {
      draft_id: "draft-quick-456",
      revision: 1,
      brief: {
        title: "Winter Realm",
        premise: "A frozen wasteland.",
      },
      stages: {} as DraftState["stages"],
      diagnostics: [],
      is_published: false,
    };

    const createSpy = vi
      .spyOn(defaultApiClient, "createQuickDraft")
      .mockResolvedValue(mockDraft);

    render(
      <MemoryRouter>
        <QuickPromptForm />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Quick Prompt Builder" })).toBeInTheDocument();
    expect(screen.getByLabelText(/World Premise \/ Prompt/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/World Premise \/ Prompt/i), {
      target: { value: "A frozen wasteland where ancient gods sleep under ice." },
    });

    fireEvent.click(screen.getByRole("button", { name: /Create Campaign Draft/i }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          premise: "A frozen wasteland where ancient gods sleep under ice.",
        }),
      );
    });
  });
});
