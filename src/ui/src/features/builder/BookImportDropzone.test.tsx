import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { defaultApiClient } from "../../api/client";
import type { DraftState } from "../../api/schema";
import { BookImportDropzone } from "./BookImportDropzone";

describe("BookImportDropzone", () => {
  it("renders dropzone and imports book file", async () => {
    const mockDraft: DraftState = {
      draft_id: "draft-epub-123",
      revision: 1,
      brief: {
        title: "Chronicles of the Realm",
        premise: "An epic adventure in a fractured realm.",
      },
      stages: {} as DraftState["stages"],
      diagnostics: [],
      is_published: false,
    };

    const importSpy = vi
      .spyOn(defaultApiClient, "importBook")
      .mockResolvedValue(mockDraft);

    render(
      <MemoryRouter>
        <BookImportDropzone />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /Drop in an EPUB or Book/i })).toBeInTheDocument();
    expect(screen.getByText(/Drag & Drop your \.epub, \.txt, or \.md file here/i)).toBeInTheDocument();

    const file = new File(["dummy content"], "novel.epub", { type: "application/epub+zip" });
    const input = screen.getByLabelText(/Upload EPUB or Book file/i);

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText("novel.epub")).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /Import & Synthesize World Codex/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(importSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          filename: "novel.epub",
          genre: "fantasy",
          tone: "grounded, atmospheric",
        }),
      );
    });
  });

  it("shows error for unsupported file formats", () => {
    render(
      <MemoryRouter>
        <BookImportDropzone />
      </MemoryRouter>,
    );

    const badFile = new File(["binary"], "picture.png", { type: "image/png" });
    const input = screen.getByLabelText(/Upload EPUB or Book file/i);

    fireEvent.change(input, { target: { files: [badFile] } });

    expect(screen.getByRole("alert")).toHaveTextContent(/Unsupported file format: 'picture\.png'/i);
  });
});
