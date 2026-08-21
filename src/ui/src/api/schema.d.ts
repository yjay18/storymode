/**
 * Strict TypeScript contracts for Storymode REST API (UI-02).
 */

export type CampaignMode = "faithful_story" | "custom_prompt" | "llm_decide";
export type CampaignLength = "short" | "medium" | "long" | "custom";
export type CampaignDifficulty = "story" | "normal" | "hard";
export type SourceType = "prompt" | "novel" | "plain_text" | "comic_transcript" | "custom";

export interface HealthResponse {
  status: string;
  version: string;
  ollama_reachable: boolean;
  model_text_available: boolean;
  model_image_available: boolean;
  models: string[];
}

export interface CampaignSummary {
  campaign_id: string;
  campaign_version: string;
  title: string;
  theme: string;
  source_type: SourceType;
  source_summary: string;
  default_difficulty: CampaignDifficulty;
  campaign_length: CampaignLength;
  status: "draft" | "published";
  content_fingerprint?: string;
  created_at: string;
}

export interface BuilderBrief {
  title: string;
  premise: string;
  campaign_mode?: CampaignMode;
  custom_prompt?: string | null;
  genre?: string;
  theme?: string;
  tone?: string;
  length?: CampaignLength;
  difficulty?: CampaignDifficulty;
  source_summary?: string;
  protected_facts?: string[];
}

export interface QuickPromptInput {
  premise: string;
  title?: string | null;
  campaign_mode?: CampaignMode;
  custom_prompt?: string | null;
  genre?: string | null;
  theme?: string | null;
  tone?: string | null;
  length?: CampaignLength | null;
  difficulty?: CampaignDifficulty | null;
}

export interface ImportBookInput {
  filename: string;
  content_base64: string;
  genre?: string;
  tone?: string;
}

export type DraftStage =
  | "meta_style"
  | "rules"
  | "areas"
  | "plot"
  | "characters"
  | "skills"
  | "review";

export type StageStatus = "not_started" | "running" | "valid" | "invalid" | "cancelled";

export interface StageDiagnostic {
  stage: DraftStage;
  code: string;
  message: string;
  field_path?: string | null;
  is_error: boolean;
}

export interface DraftStageState {
  stage: DraftStage;
  status: StageStatus;
  attempts: number;
  diagnostics: StageDiagnostic[];
  artifact_data?: Record<string, unknown> | null;
}

export interface DraftState {
  draft_id: string;
  revision: number;
  brief: BuilderBrief;
  stages: Record<DraftStage, DraftStageState>;
  diagnostics: StageDiagnostic[];
  is_published: boolean;
  published_campaign_id?: string | null;
}

export interface ValidationReport {
  draft_id: string;
  is_valid: boolean;
  is_publish_ready: boolean;
  errors: StageDiagnostic[];
  warnings: StageDiagnostic[];
}

export interface PublishResult {
  campaign_id: string;
  campaign_dir: string;
  fingerprint: string;
}

export interface SaveSlotSummary {
  save_id: string;
  campaign_id: string;
  campaign_fingerprint: string;
  slot_number: number;
  player_name: string;
  current_area_id: string;
  in_combat: boolean;
  revision: number;
  created_at: string;
  updated_at: string;
}

export interface CreateSaveRequest {
  player_name: string;
  background_id: string;
  attributes: Record<string, number>;
  slot_number?: number;
}

export interface RuntimeStateResponse {
  save_id: string;
  campaign_id: string;
  revision: number;
  player: {
    name: string;
    level: number;
    hp: number;
    max_hp: number;
    mana: number;
    max_mana: number;
    attributes: Record<string, number>;
    equipped_skills: string[];
    inventory: Array<{ item_id: string; quantity: number }>;
  };
  current_area_id: string;
  in_combat: boolean;
  active_combat_id?: string | null;
}

export interface ActionRequest {
  command_id: string;
  raw_input: string;
  expected_revision: number;
}

export interface ActionResponse {
  command_id: string;
  status: "success" | "check_required" | "rejected" | "combat_started";
  narration: string;
  outcome_summary: string;
  new_revision: number;
  pending_check?: {
    check_id: string;
    skill_or_attribute: string;
    dc: number;
    stakes_description: string;
    allow_luck_reroll: boolean;
  } | null;
}

export interface CheckResolutionRequest {
  command_id: string;
  use_luck: boolean;
  expected_revision: number;
}

export interface CombatStateResponse {
  combat_id: string;
  round: number;
  turn_order: string[];
  active_entity_id: string;
  is_player_turn: boolean;
  enemies: Array<{
    enemy_id: string;
    name: string;
    hp: number;
    max_hp: number;
    is_defeated: boolean;
  }>;
  available_skills: string[];
  can_flee: boolean;
  can_yield: boolean;
  is_finished: boolean;
  outcome?: "victory" | "defeat" | "fled" | "yielded" | null;
}
