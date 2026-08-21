import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import type {
  CampaignDifficulty,
  CampaignLength,
  CampaignMode,
  QuickPromptInput,
} from "../../api/schema";
import { BuilderNav } from "./BuilderNav";

export function QuickPromptForm(): React.JSX.Element {
  const navigate = useNavigate();

  const [premise, setPremise] = useState<string>("");
  const [title, setTitle] = useState<string>("");
  const [campaignMode, setCampaignMode] = useState<CampaignMode>("llm_decide");
  const [length, setLength] = useState<CampaignLength>("medium");
  const [difficulty, setDifficulty] = useState<CampaignDifficulty>("normal");

  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!premise.trim()) {
      setError("Campaign premise is required.");
      return;
    }

    setSubmitting(true);
    setError(null);

    const input: QuickPromptInput = {
      premise: premise.trim(),
      title: title.trim() ? title.trim() : null,
      campaign_mode: campaignMode,
      length,
      difficulty,
    };

    try {
      const draft = await defaultApiClient.createQuickDraft(input);
      navigate(`/builder/drafts/${draft.draft_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create quick draft");
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      aria-label="Quick Prompt Campaign Form"
      style={{
        maxWidth: "700px",
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        gap: "1.5rem",
      }}
    >
      <BuilderNav />
      <div>
        <h1 style={{ marginBottom: "0.5rem" }}>Quick Prompt Builder</h1>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
          Enter a world premise or story idea. Storymode will generate a complete campaign
          pack while maintaining full deterministic rule validity.
        </p>
      </div>

      {error && (
        <div
          role="alert"
          style={{
            padding: "var(--space-3)",
            backgroundColor: "rgba(248, 113, 113, 0.15)",
            border: "1px solid var(--color-danger)",
            borderRadius: "var(--radius-md)",
            color: "var(--color-danger)",
            fontSize: "var(--font-size-sm)",
          }}
        >
          {error}
        </div>
      )}

      {/* Premise */}
      <div>
        <label
          htmlFor="quick-premise"
          style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
        >
          World Premise / Prompt <span style={{ color: "var(--color-danger)" }}>*</span>
        </label>
        <textarea
          id="quick-premise"
          rows={6}
          value={premise}
          onChange={(e) => setPremise(e.target.value)}
          placeholder="e.g. A cursed winter has fallen upon the northern valleys. An ancient order of guardians must rekindle the mountain beacon before the frost demons descend..."
          required
          maxLength={4000}
        />
      </div>

      {/* Optional Title */}
      <div>
        <label
          htmlFor="quick-title"
          style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
        >
          Working Title (Optional)
        </label>
        <input
          id="quick-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Leave blank to let the model generate a title"
          maxLength={100}
        />
      </div>

      {/* Mode, Length, Difficulty */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
        <div>
          <label
            htmlFor="quick-mode"
            style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
          >
            Mode
          </label>
          <select
            id="quick-mode"
            value={campaignMode}
            onChange={(e) => setCampaignMode(e.target.value as CampaignMode)}
          >
            <option value="llm_decide">LLM Decide</option>
            <option value="faithful_story">Faithful</option>
            <option value="custom_prompt">Custom</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="quick-length"
            style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
          >
            Length
          </label>
          <select
            id="quick-length"
            value={length}
            onChange={(e) => setLength(e.target.value as CampaignLength)}
          >
            <option value="short">Short</option>
            <option value="medium">Medium</option>
            <option value="long">Long</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="quick-difficulty"
            style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
          >
            Difficulty
          </label>
          <select
            id="quick-difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as CampaignDifficulty)}
          >
            <option value="story">Story</option>
            <option value="normal">Normal</option>
            <option value="hard">Hard</option>
          </select>
        </div>
      </div>

      {/* Submit */}
      <div style={{ marginTop: "1rem" }}>
        <button
          type="submit"
          disabled={submitting}
          style={{
            backgroundColor: "var(--color-accent)",
            color: "var(--color-bg-base)",
            fontWeight: "600",
            padding: "var(--space-3) var(--space-6)",
          }}
        >
          {submitting ? "Generating Draft..." : "Create Campaign Draft →"}
        </button>
      </div>
    </form>
  );
}
