import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { HealthResponse } from "../../api/schema";
import { PreflightCard } from "./PreflightCard";

describe("PreflightCard", () => {
  it("renders loading state", () => {
    render(<PreflightCard health={null} loading={true} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("Checking local system readiness...")).toBeInTheDocument();
  });

  it("renders error state with retry button", () => {
    const onRetry = vi.fn();
    render(<PreflightCard health={null} loading={false} error="Ollama is down" onRetry={onRetry} />);
    expect(screen.getByText("Local Service Unavailable")).toBeInTheDocument();
    expect(screen.getByText("Ollama is down")).toBeInTheDocument();
  });

  it("renders ready state when all services are healthy", () => {
    const health: HealthResponse = {
      status: "ok",
      version: "1.0.0",
      ollama_reachable: true,
      model_text_available: true,
      model_image_available: true,
      models: ["llama3.1:8b"],
    };
    render(<PreflightCard health={health} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("Local System Readiness")).toBeInTheDocument();
    expect(screen.getByText("Ready (v1.0.0)")).toBeInTheDocument();
    expect(screen.getByText("Connected (Loopback)")).toBeInTheDocument();
    expect(screen.getAllByText("Available")).toHaveLength(2);
  });
});
