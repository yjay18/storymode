/**
 * Strict TypeScript contracts for Storymode REST API.
 *
 * These mirror the served Pydantic schemas in `src/api/schemas/*.py` and the domain
 * models they embed. The play-path types are validated against `app.openapi()` by
 * `tests/integration/api/test_ui_client_routes.py`.
 */

export type CampaignMode = "faithful_story" | "custom_prompt" | "llm_decide";
export type CampaignLength = "short" | "medium" | "long" | "custom";
export type CampaignStatus = "draft" | "published";
export type DefaultDifficulty = "story" | "normal" | "hard";
/** Alias kept for builder forms; identical to the served DefaultDifficulty union. */
export type CampaignDifficulty = DefaultDifficulty;
export type StatName =
  | "strength"
  | "dexterity"
  | "intelligence"
  | "charisma"
  | "constitution"
  | "wisdom";

export interface HealthResponse {
  status: string;
  version: string;
  ollama_reachable: boolean;
  model_text_available: boolean;
  model_image_available: boolean;
  models: string[];
}

// --- Campaigns (src/api/schemas/campaigns.py) ---

export interface CampaignSummary {
  campaign_id: string;
  title: string;
  description: string;
  version: string;
  status: CampaignStatus;
  campaign_length: CampaignLength;
  content_fingerprint?: string | null;
}

export interface BackgroundDefinition {
  id: string;
  name: string;
  description: string;
  stat_bonus: StatName;
  stat_bonus_value: number;
  starting_skill_ids: string[];
  starting_item_ids: string[];
  starting_fact_ids: string[];
}

export interface CampaignDetail {
  campaign_id: string;
  title: string;
  description: string;
  version: string;
  status: CampaignStatus;
  campaign_length: CampaignLength;
  content_fingerprint?: string | null;
  backgrounds: BackgroundDefinition[];
  area_count: number;
  has_valid_point_buy: boolean;
}

// --- Builder (src/api/schemas/builder.py) ---

export interface BuilderBrief {
  title: string;
  premise: string;
  campaign_mode?: CampaignMode;
  custom_prompt?: string | null;
  genre?: string;
  theme?: string;
  tone?: string;
  length?: CampaignLength;
  difficulty?: DefaultDifficulty;
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
  difficulty?: DefaultDifficulty | null;
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

// --- Saves (src/api/schemas/saves.py) ---

export interface CreateSaveRequest {
  campaign_id: string;
  slot_kind?: string;
  slot_name: string;
  player_name: string;
  background_id: string;
  stats: Record<string, number>;
  difficulty?: string;
  command_id: string;
  campaign_fingerprint?: string | null;
}

export interface SaveSummaryResponse {
  save_id: string;
  campaign_id: string;
  revision: number;
  player_name: string;
  difficulty: DefaultDifficulty;
  current_area_id: string;
  slot_name: string;
  slot_kind: string;
}

// --- Shared domain models (src/domain/models) ---

export interface ResourceValue {
  current: number;
  maximum: number;
}

export interface StatusInstance {
  status_id: string;
  duration_remaining?: number | null;
  magnitude?: number | null;
  source_entity_id?: string | null;
}

export interface KnownCombatSkill {
  skill_id: string;
  level: number;
  acquisition_source_id: string;
}

export type EffectKind = string;

export interface EffectDefinition {
  effect_id: string;
  kind: EffectKind;
  magnitude: number;
  duration?: number | null;
  status_id?: string | null;
  stacking_key?: string | null;
}

export interface CheckOutcomes {
  natural_1: EffectDefinition[];
  low: EffectDefinition[];
  standard: EffectDefinition[];
  strong: EffectDefinition[];
  natural_20: EffectDefinition[];
}

export interface PendingCheck {
  check_id: string;
  source_command_id: string;
  source_revision: number;
  original_input: string;
  resolved_operation: string;
  actor_id: string;
  target_ids: string[];
  stat?: StatName | null;
  skill_id?: string | null;
  named_modifiers: Record<string, number>;
  semantic_difficulty: string;
  base_dc: number;
  difficulty_adjustment: number;
  final_dc: number;
  stakes: string;
  allowed_outcomes: CheckOutcomes;
}

// --- Actions (src/api/schemas/actions.py) ---

export interface SubmitActionRequest {
  campaign_id: string;
  save_id: string;
  command_id: string;
  expected_revision: number;
  player_text: string;
}

export interface SubmitActionResponse {
  save_id: string;
  campaign_id: string;
  revision: number;
  has_pending_check: boolean;
  rejection_reason?: string | null;
  pending_check?: PendingCheck | null;
  narration?: string | null;
}

export interface ResolveCheckRequest {
  campaign_id: string;
  save_id: string;
  command_id: string;
  expected_revision: number;
  use_luck?: boolean;
}

export interface ResolveCheckResponse {
  save_id: string;
  campaign_id: string;
  revision: number;
  roll: number;
  band: string;
  narration?: string | null;
}

export interface CancelCheckRequest {
  campaign_id: string;
  save_id: string;
  command_id: string;
  expected_revision: number;
}

export interface CancelCheckResponse {
  save_id: string;
  campaign_id: string;
  revision: number;
  narration?: string | null;
}

// --- Combat (src/api/schemas/combat.py + domain/models/combat_state.py) ---

export type CombatPhase = "active" | "resolving" | "victory" | "defeat" | "escaped" | "yielded";
export type ParticipantSide = "party" | "enemy" | "neutral";
export type CombatCommandKind = "use_skill" | "defend" | "flee" | "yield";
export type TargetRule =
  | "self"
  | "single_ally"
  | "single_enemy"
  | "all_allies"
  | "all_enemies"
  | "any";

export interface CombatParticipant {
  hp: ResourceValue;
  armour: ResourceValue;
  mana: ResourceValue;
  statuses: StatusInstance[];
  known_combat_skills: KnownCombatSkill[];
  combat_loadout: string[];
  faction_id?: string | null;
  side: ParticipantSide;
}

export interface TieBreakRecord {
  participant_id: string;
  roll_total: number;
}

export interface CombatState {
  encounter_id: string;
  phase: CombatPhase;
  round: number;
  order: string[];
  current_index: number;
  participants: Record<string, CombatParticipant>;
  tie_break_records: TieBreakRecord[];
  escape_policy?: string | null;
  yield_policy?: string | null;
  encounter_modifiers: string[];
  origin_ids: string[];
}

export interface AllowedCombatAction {
  action_kind: CombatCommandKind;
  skill_id?: string | null;
  skill_name?: string | null;
  mana_cost: number;
  target_rule?: TargetRule | null;
  valid_target_ids: string[];
  description?: string | null;
}

export interface StartCombatRequest {
  campaign_id: string;
  save_id: string;
  encounter_id: string;
  command_id: string;
  expected_revision: number;
}

export interface UseSkillRequest {
  campaign_id: string;
  save_id: string;
  skill_id: string;
  target_ids: string[];
  command_id: string;
  expected_revision: number;
}

export interface DefendRequest {
  campaign_id: string;
  save_id: string;
  command_id: string;
  expected_revision: number;
}

export interface FleeRequest {
  campaign_id: string;
  save_id: string;
  command_id: string;
  expected_revision: number;
}

export interface YieldRequest {
  campaign_id: string;
  save_id: string;
  command_id: string;
  expected_revision: number;
}

export interface CombatViewResponse {
  save_id: string;
  campaign_id: string;
  revision: number;
  combat?: CombatState | null;
  allowed_actions: AllowedCombatAction[];
}

export interface CombatResponse {
  save_id: string;
  campaign_id: string;
  revision: number;
  combat?: CombatState | null;
  allowed_actions: AllowedCombatAction[];
  is_terminal: boolean;
  outcome?: string | null;
  logs: string[];
}

// --- Progression (src/api/schemas/progression.py) ---

export interface GrantXpRequest {
  command_id: string;
  expected_revision: number;
  xp_amount: number;
}

export interface UpgradeSkillRequest {
  command_id: string;
  expected_revision: number;
  skill_id: string;
  target_id?: string | null;
}

export interface SetLoadoutRequest {
  command_id: string;
  expected_revision: number;
  loadout: string[];
  target_id?: string | null;
}

export interface PerformFusionRequest {
  command_id: string;
  expected_revision: number;
  recipe_id: string;
  companion_id?: string | null;
}

export interface KnownSkillView {
  skill_id: string;
  current_level: number;
}

export interface InventoryItemView {
  item_id: string;
  quantity: number;
}

export interface ProgressionReceiptView {
  command_id: string;
  committed_revision: number;
  result_kind: string;
  safe_result_summary: string;
}

export interface PlayerProgressionView {
  id: string;
  name: string;
  level: number;
  xp: number;
  upgrade_tokens: number;
  hp_current: number;
  hp_maximum: number;
  mana_current: number;
  mana_maximum: number;
  combat_loadout: string[];
  known_skills: KnownSkillView[];
  inventory: InventoryItemView[];
}

export interface ProgressionViewResponse {
  save_id: string;
  revision: number;
  player: PlayerProgressionView;
}

export interface ProgressionMutationResponse {
  save_id: string;
  revision: number;
  receipt: ProgressionReceiptView;
  player: PlayerProgressionView;
}

// --- Party (src/api/schemas/party.py) ---

export interface RecruitCompanionRequest {
  command_id: string;
  expected_revision: number;
  companion_id: string;
}

export interface ActivateCompanionRequest {
  command_id: string;
  expected_revision: number;
  companion_id: string;
}

export interface DeactivateCompanionRequest {
  command_id: string;
  expected_revision: number;
  companion_id: string;
}

export interface LeaveCompanionRequest {
  command_id: string;
  expected_revision: number;
  companion_id: string;
}

export interface CompanionView {
  id: string;
  name: string;
  role: string;
  life_state: string;
  is_available: boolean;
  is_active: boolean;
  hp_current: number;
  hp_maximum: number;
  mana_current: number;
  mana_maximum: number;
  combat_loadout: string[];
  known_skill_ids: string[];
}

export interface PartyViewResponse {
  protagonist_id: string;
  active_companion_ids: string[];
  companions: CompanionView[];
}

export interface PartyReceiptView {
  command_id: string;
  committed_revision: number;
  result_kind: string;
  safe_result_summary: string;
}

export interface PartyMutationResponse {
  save_id: string;
  revision: number;
  receipt: PartyReceiptView;
  party: PartyViewResponse;
}

// --- Plot (src/api/schemas/plot.py) ---

export interface ResolveOpportunityRequest {
  command_id: string;
  expected_revision: number;
  opportunity_id: string;
  outcome_id: string;
}

export interface MilestoneView {
  id: string;
  status: string;
  is_current: boolean;
}

export interface OpportunityView {
  id: string;
  title: string;
  description: string;
  status: string;
  parent_milestone_id: string;
  allowed_outcome_ids: string[];
  is_resolved: boolean;
}

export interface ClockView {
  id: string;
  current: number;
  maximum: number;
  completed: boolean;
}

export interface PlotReceiptView {
  command_id: string;
  committed_revision: number;
  result_kind: string;
  safe_result_summary: string;
}

export interface PlotViewResponse {
  save_id: string;
  revision: number;
  current_milestone_ids: string[];
  milestones: MilestoneView[];
  opportunities: OpportunityView[];
  clocks: ClockView[];
  ending_state?: string | null;
}

export interface PlotMutationResponse {
  save_id: string;
  revision: number;
  receipt: PlotReceiptView;
  plot: PlotViewResponse;
}
