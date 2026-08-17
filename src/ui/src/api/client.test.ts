import { describe, expect, it, vi } from "vitest";
import { ApiClient } from "./client";
import { createCommandTracker } from "./commands";
import {
  ApiClientError,
  ApiConflictError,
  ApiNotFoundError,
  ApiValidationError,
} from "./errors";

describe("ApiClient", () => {
  it("rejects non-loopback remote URLs in constructor", () => {
    expect(() => new ApiClient("https://api.remote.com")).toThrow(ApiClientError);
    expect(() => new ApiClient("http://127.0.0.1:8000")).not.toThrow();
    expect(() => new ApiClient("http://localhost:8000")).not.toThrow();
  });

  it("handles successful json requests", async () => {
    const mockHealth = {
      status: "ok",
      version: "1.0.0",
      ollama_reachable: true,
      model_text_available: true,
      model_image_available: false,
      models: ["llama3.1:8b"],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockHealth),
    });

    const client = new ApiClient();
    const result = await client.getHealth();
    expect(result.status).toBe("ok");
    expect(result.ollama_reachable).toBe(true);
  });

  it("maps 404 responses to ApiNotFoundError", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: () => Promise.resolve({ code: "not_found", message: "Draft missing" }),
    });

    const client = new ApiClient();
    await expect(client.getDraft("nonexistent")).rejects.toThrow(ApiNotFoundError);
  });

  it("maps 409 responses to ApiConflictError", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      statusText: "Conflict",
      json: () => Promise.resolve({ code: "conflict", message: "Revision mismatch" }),
    });

    const client = new ApiClient();
    await expect(
      client.editStage("draft-1", "meta_style", {}, 1),
    ).rejects.toThrow(ApiConflictError);
  });

  it("maps 422 responses to ApiValidationError", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: "Unprocessable",
      json: () => Promise.resolve({ code: "validation_error", message: "Invalid payload" }),
    });

    const client = new ApiClient();
    await expect(
      client.createGuidedDraft({ title: "", premise: "" }),
    ).rejects.toThrow(ApiValidationError);
  });
});

describe("CommandTracker", () => {
  it("maintains same command ID for same intent across retries", () => {
    const tracker = createCommandTracker();
    const cmdId1 = tracker.getOrGenerate("attack-goblin-1");
    const cmdId2 = tracker.getOrGenerate("attack-goblin-1");
    expect(cmdId1).toBe(cmdId2);

    tracker.consume("attack-goblin-1");
    const cmdId3 = tracker.getOrGenerate("attack-goblin-1");
    expect(cmdId3).not.toBe(cmdId1);
  });
});
