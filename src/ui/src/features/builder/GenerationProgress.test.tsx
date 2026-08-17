import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { DraftStage, DraftStageState } from "../../api/schema";
import { GenerationProgress } from "./GenerationProgress";

describe("GenerationProgress", () => {
  it("renders all stages with their status and responds to generation triggers", () => {
    const stages: Partial<Record<DraftStage, DraftStageState>> = {
      meta_style: {
        stage: "meta_style",
        status: "valid",
        attempts: 1,
        diagnostics: [],
      },
      rules: {
        stage: "rules",
        status: "not_started",
        attempts: 0,
        diagnostics: [],
      },
    };

    const onGenerate = vi.fn();
    const onCancel = vi.fn();

    render(
      <GenerationProgress
        stages={stages as Record<DraftStage, DraftStageState>}
        generating={false}
        onGenerate={onGenerate}
        onCancel={onCancel}
      />,
    );

    expect(screen.getByText("1. Meta & Style Bible")).toBeInTheDocument();
    expect(screen.getByText("✓ Valid")).toBeInTheDocument();
    expect(screen.getByText("2. World Rules & Factions")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Start \/ Continue All Stages/i }));
    expect(onGenerate).toHaveBeenCalled();
  });
});
