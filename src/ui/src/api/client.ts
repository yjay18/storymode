/**
 * Resilient typed local fetch client for Storymode API.
 *
 * Every play path here is asserted against the served `app.openapi()` paths by
 * `tests/integration/api/test_ui_client_routes.py`; keep them as `/api/v1/...`
 * template literals so the drift test can extract and verify them.
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
  BuilderBrief,
  CampaignDetail,
  CampaignSummary,
  CancelCheckRequest,
  CancelCheckResponse,
  CombatResponse,
  CombatViewResponse,
  CreateSaveRequest,
  DefendRequest,
  DraftStage,
  DraftState,
  FleeRequest,
  FusionRecipeListResponse,
  GrantXpRequest,
  HealthResponse,
  ImportBookInput,
  PartyMutationResponse,
  PartyViewResponse,
  PerformFusionRequest,
  PlotMutationResponse,
  PlotViewResponse,
  ProgressionMutationResponse,
  ProgressionViewResponse,
  PublishResult,
  QuickPromptInput,
  RecruitCompanionRequest,
  ResolveCheckRequest,
  ResolveCheckResponse,
  ResolveOpportunityRequest,
  SaveSummaryResponse,
  SetLoadoutRequest,
  StartCombatRequest,
  SubmitActionRequest,
  SubmitActionResponse,
  UpgradeSkillRequest,
  UseSkillRequest,
  ValidationReport,
  YieldRequest,
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

  private post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, { method: "POST", body: JSON.stringify(body) });
  }

  // --- Health ---
  getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  // --- Campaigns ---
  listCampaigns(): Promise<CampaignSummary[]> {
    return this.request<CampaignSummary[]>("/api/v1/campaigns");
  }

  getCampaign(campaignId: string): Promise<CampaignDetail> {
    return this.request<CampaignDetail>(`/api/v1/campaigns/${campaignId}`);
  }

  // --- Builder ---
  listDrafts(): Promise<DraftState[]> {
    return this.request<DraftState[]>("/api/v1/builder/drafts");
  }

  getDraft(draftId: string): Promise<DraftState> {
    return this.request<DraftState>(`/api/v1/builder/drafts/${draftId}`);
  }

  createGuidedDraft(brief: BuilderBrief): Promise<DraftState> {
    return this.post<DraftState>("/api/v1/builder/drafts/guided", { brief });
  }

  createQuickDraft(quickInput: QuickPromptInput): Promise<DraftState> {
    return this.post<DraftState>("/api/v1/builder/drafts/quick", { quick_input: quickInput });
  }

  importBook(payload: ImportBookInput): Promise<DraftState> {
    return this.post<DraftState>("/api/v1/builder/drafts/import", payload);
  }

  generateDraftStage(draftId: string, stage?: DraftStage): Promise<DraftState> {
    return this.post<DraftState>(`/api/v1/builder/drafts/${draftId}/generate`, { stage });
  }

  cancelDraft(draftId: string): Promise<DraftState> {
    return this.request<DraftState>(`/api/v1/builder/drafts/${draftId}/cancel`, { method: "POST" });
  }

  editStage(
    draftId: string,
    stage: DraftStage,
    artifactData: Record<string, unknown>,
    expectedRevision: number,
  ): Promise<DraftState> {
    return this.request<DraftState>(`/api/v1/builder/drafts/${draftId}/stages/${stage}`, {
      method: "PUT",
      body: JSON.stringify({ expected_revision: expectedRevision, artifact_data: artifactData }),
    });
  }

  validateDraft(draftId: string): Promise<ValidationReport> {
    return this.request<ValidationReport>(`/api/v1/builder/drafts/${draftId}/validate`);
  }

  publishDraft(draftId: string, confirmed: boolean = false): Promise<PublishResult> {
    return this.post<PublishResult>(`/api/v1/builder/drafts/${draftId}/publish`, { confirmed });
  }

  // --- Saves ---
  createSave(payload: CreateSaveRequest): Promise<SaveSummaryResponse> {
    return this.post<SaveSummaryResponse>("/api/v1/saves", payload);
  }

  getSave(campaignId: string, saveId: string): Promise<SaveSummaryResponse> {
    return this.request<SaveSummaryResponse>(`/api/v1/saves/${campaignId}/${saveId}`);
  }

  // --- Actions & Exploration ---
  submitAction(payload: SubmitActionRequest): Promise<SubmitActionResponse> {
    return this.post<SubmitActionResponse>("/api/v1/actions/submit", payload);
  }

  resolveCheck(payload: ResolveCheckRequest): Promise<ResolveCheckResponse> {
    return this.post<ResolveCheckResponse>("/api/v1/actions/resolve-check", payload);
  }

  cancelCheck(payload: CancelCheckRequest): Promise<CancelCheckResponse> {
    return this.post<CancelCheckResponse>("/api/v1/actions/cancel-check", payload);
  }

  // --- Combat ---
  getCombatView(campaignId: string, saveId: string): Promise<CombatViewResponse> {
    return this.request<CombatViewResponse>(
      `/api/v1/combat/view?campaign_id=${campaignId}&save_id=${saveId}`,
    );
  }

  startCombat(payload: StartCombatRequest): Promise<CombatResponse> {
    return this.post<CombatResponse>("/api/v1/combat/start", payload);
  }

  useSkill(payload: UseSkillRequest): Promise<CombatResponse> {
    return this.post<CombatResponse>("/api/v1/combat/skill", payload);
  }

  defend(payload: DefendRequest): Promise<CombatResponse> {
    return this.post<CombatResponse>("/api/v1/combat/defend", payload);
  }

  flee(payload: FleeRequest): Promise<CombatResponse> {
    return this.post<CombatResponse>("/api/v1/combat/flee", payload);
  }

  yieldCombat(payload: YieldRequest): Promise<CombatResponse> {
    return this.post<CombatResponse>("/api/v1/combat/yield", payload);
  }

  // --- Progression ---
  getProgression(campaignId: string, saveId: string): Promise<ProgressionViewResponse> {
    return this.request<ProgressionViewResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/progression`,
    );
  }

  listFusionRecipes(campaignId: string, saveId: string): Promise<FusionRecipeListResponse> {
    return this.request<FusionRecipeListResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/progression/fusion`,
    );
  }

  grantXp(
    campaignId: string,
    saveId: string,
    payload: GrantXpRequest,
  ): Promise<ProgressionMutationResponse> {
    return this.post<ProgressionMutationResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/progression/xp`,
      payload,
    );
  }

  upgradeSkill(
    campaignId: string,
    saveId: string,
    payload: UpgradeSkillRequest,
  ): Promise<ProgressionMutationResponse> {
    return this.post<ProgressionMutationResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/progression/upgrade`,
      payload,
    );
  }

  setLoadout(
    campaignId: string,
    saveId: string,
    payload: SetLoadoutRequest,
  ): Promise<ProgressionMutationResponse> {
    return this.post<ProgressionMutationResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/progression/loadout`,
      payload,
    );
  }

  performFusion(
    campaignId: string,
    saveId: string,
    payload: PerformFusionRequest,
  ): Promise<ProgressionMutationResponse> {
    return this.post<ProgressionMutationResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/progression/fusion`,
      payload,
    );
  }

  // --- Party ---
  getParty(campaignId: string, saveId: string): Promise<PartyViewResponse> {
    return this.request<PartyViewResponse>(`/api/v1/saves/${campaignId}/${saveId}/party`);
  }

  recruitCompanion(
    campaignId: string,
    saveId: string,
    payload: RecruitCompanionRequest,
  ): Promise<PartyMutationResponse> {
    return this.post<PartyMutationResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/party/recruit`,
      payload,
    );
  }

  activateCompanion(
    campaignId: string,
    saveId: string,
    payload: RecruitCompanionRequest,
  ): Promise<PartyMutationResponse> {
    return this.post<PartyMutationResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/party/activate`,
      payload,
    );
  }

  deactivateCompanion(
    campaignId: string,
    saveId: string,
    payload: RecruitCompanionRequest,
  ): Promise<PartyMutationResponse> {
    return this.post<PartyMutationResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/party/deactivate`,
      payload,
    );
  }

  leaveCompanion(
    campaignId: string,
    saveId: string,
    payload: RecruitCompanionRequest,
  ): Promise<PartyMutationResponse> {
    return this.post<PartyMutationResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/party/leave`,
      payload,
    );
  }

  // --- Plot ---
  getPlot(campaignId: string, saveId: string): Promise<PlotViewResponse> {
    return this.request<PlotViewResponse>(`/api/v1/saves/${campaignId}/${saveId}/plot`);
  }

  resolveOpportunity(
    campaignId: string,
    saveId: string,
    payload: ResolveOpportunityRequest,
  ): Promise<PlotMutationResponse> {
    return this.post<PlotMutationResponse>(
      `/api/v1/saves/${campaignId}/${saveId}/plot/opportunities/resolve`,
      payload,
    );
  }
}

export const defaultApiClient = new ApiClient();
