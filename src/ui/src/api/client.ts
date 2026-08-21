/**
 * Resilient typed local fetch client for Storymode API (UI-02).
 */

import {
  ApiClientError,
  ApiConflictError,
  ApiHttpError,
  ApiNetworkError,
  ApiNotFoundError,
  ApiTimeoutError,
  ApiValidationError,
} from "./errors";
import type {
  ActionRequest,
  ActionResponse,
  BuilderBrief,
  CampaignSummary,
  CheckResolutionRequest,
  CombatStateResponse,
  CreateSaveRequest,
  DraftStage,
  DraftState,
  HealthResponse,
  ImportBookInput,
  PublishResult,
  QuickPromptInput,
  RuntimeStateResponse,
  SaveSlotSummary,
  ValidationReport,
} from "./schema";

const DEFAULT_TIMEOUT_MS = 30000;

export class ApiClient {
  readonly baseUrl: string;

  constructor(baseUrl: string = "") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    if (this.baseUrl) {
      try {
        const parsed = new URL(this.baseUrl);
        const host = parsed.hostname.toLowerCase();
        if (
          host !== "127.0.0.1" &&
          host !== "localhost" &&
          host !== "::1" &&
          host !== "0.0.0.0"
        ) {
          throw new ApiClientError(
            `Refusing non-loopback base URL: '${this.baseUrl}'. Storymode only allows local connections.`,
          );
        }
      } catch (e) {
        if (e instanceof ApiClientError) throw e;
        // Relative base URLs are allowed
      }
    }
  }

  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

    // If caller provided a signal, link it
    if (options.signal) {
      options.signal.addEventListener("abort", () => controller.abort());
    }

    try {
      const res = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (res.ok) {
        if (res.status === 204) {
          return undefined as T;
        }
        return (await res.json()) as T;
      }

      // Handle error responses
      let errorBody: unknown;
      try {
        errorBody = await res.json();
      } catch {
        errorBody = { message: await res.text() };
      }

      const message =
        typeof errorBody === "object" && errorBody !== null && "message" in errorBody
          ? String((errorBody as { message: unknown }).message)
          : `HTTP Error ${res.status}: ${res.statusText}`;

      if (res.status === 404) {
        throw new ApiNotFoundError(message, errorBody);
      }
      if (res.status === 409) {
        throw new ApiConflictError(message, errorBody);
      }
      if (res.status === 422) {
        throw new ApiValidationError(message, errorBody);
      }
      throw new ApiHttpError(res.status, "http_error", message, errorBody);
    } catch (e) {
      clearTimeout(timeoutId);
      if (e instanceof ApiClientError) {
        throw e;
      }
      if (e instanceof Error && e.name === "AbortError") {
        throw new ApiTimeoutError("Request timed out or was cancelled");
      }
      throw new ApiNetworkError("Network request failed", e);
    }
  }

  // --- Health ---
  getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/api/v1/health");
  }

  // --- Campaigns ---
  listCampaigns(): Promise<CampaignSummary[]> {
    return this.request<CampaignSummary[]>("/api/v1/campaigns");
  }

  getCampaign(campaignId: string): Promise<CampaignSummary> {
    return this.request<CampaignSummary>(`/api/v1/campaigns/${campaignId}`);
  }

  // --- Builder ---
  listDrafts(): Promise<DraftState[]> {
    return this.request<DraftState[]>("/api/v1/builder/drafts");
  }

  getDraft(draftId: string): Promise<DraftState> {
    return this.request<DraftState>(`/api/v1/builder/drafts/${draftId}`);
  }

  createGuidedDraft(brief: BuilderBrief): Promise<DraftState> {
    return this.request<DraftState>("/api/v1/builder/drafts/guided", {
      method: "POST",
      body: JSON.stringify({ brief }),
    });
  }

  createQuickDraft(quickInput: QuickPromptInput): Promise<DraftState> {
    return this.request<DraftState>("/api/v1/builder/drafts/quick", {
      method: "POST",
      body: JSON.stringify({ quick_input: quickInput }),
    });
  }

  importBook(payload: ImportBookInput): Promise<DraftState> {
    return this.request<DraftState>("/api/v1/builder/drafts/import", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  generateDraftStage(draftId: string, stage?: DraftStage): Promise<DraftState> {
    return this.request<DraftState>(`/api/v1/builder/drafts/${draftId}/generate`, {
      method: "POST",
      body: JSON.stringify({ stage }),
    });
  }

  cancelDraft(draftId: string): Promise<DraftState> {
    return this.request<DraftState>(`/api/v1/builder/drafts/${draftId}/cancel`, {
      method: "POST",
    });
  }

  editStage(
    draftId: string,
    stage: DraftStage,
    artifactData: Record<string, unknown>,
    expectedRevision: number,
  ): Promise<DraftState> {
    return this.request<DraftState>(`/api/v1/builder/drafts/${draftId}/stages/${stage}`, {
      method: "PUT",
      body: JSON.stringify({
        expected_revision: expectedRevision,
        artifact_data: artifactData,
      }),
    });
  }

  validateDraft(draftId: string): Promise<ValidationReport> {
    return this.request<ValidationReport>(`/api/v1/builder/drafts/${draftId}/validate`);
  }

  publishDraft(draftId: string, confirmed: boolean = false): Promise<PublishResult> {
    return this.request<PublishResult>(`/api/v1/builder/drafts/${draftId}/publish`, {
      method: "POST",
      body: JSON.stringify({ confirmed }),
    });
  }

  // --- Saves ---
  listSaves(campaignId: string): Promise<SaveSlotSummary[]> {
    return this.request<SaveSlotSummary[]>(`/api/v1/campaigns/${campaignId}/saves`);
  }

  createSave(campaignId: string, payload: CreateSaveRequest): Promise<RuntimeStateResponse> {
    return this.request<RuntimeStateResponse>(`/api/v1/campaigns/${campaignId}/saves`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  getSave(campaignId: string, saveId: string): Promise<RuntimeStateResponse> {
    return this.request<RuntimeStateResponse>(
      `/api/v1/campaigns/${campaignId}/saves/${saveId}`,
    );
  }

  // --- Actions & Exploration ---
  executeAction(
    campaignId: string,
    saveId: string,
    payload: ActionRequest,
  ): Promise<ActionResponse> {
    return this.request<ActionResponse>(
      `/api/v1/campaigns/${campaignId}/saves/${saveId}/actions`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  resolveCheck(
    campaignId: string,
    saveId: string,
    checkId: string,
    payload: CheckResolutionRequest,
  ): Promise<ActionResponse> {
    return this.request<ActionResponse>(
      `/api/v1/campaigns/${campaignId}/saves/${saveId}/checks/${checkId}/resolve`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  // --- Combat ---
  getCombatState(
    campaignId: string,
    saveId: string,
    combatId: string,
  ): Promise<CombatStateResponse> {
    return this.request<CombatStateResponse>(
      `/api/v1/campaigns/${campaignId}/saves/${saveId}/combat/${combatId}`,
    );
  }
}

export const defaultApiClient = new ApiClient();
