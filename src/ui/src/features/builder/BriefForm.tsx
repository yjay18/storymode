import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import type {
  BuilderBrief,
  CampaignDifficulty,
  CampaignLength,
  CampaignMode,
} from "../../api/schema";
import { BuilderNav } from "./BuilderNav";

export function BriefForm(): React.JSX.Element {
  const navigate = useNavigate();

  const [title, setTitle] = useState<string>("");
  const [premise, setPremise] = useState<string>("");
  const [campaignMode, setCampaignMode] = useState<CampaignMode>("llm_decide");
  const [customPrompt, setCustomPrompt] = useState<string>("");
  const [genre, setGenre] = useState<string>("dark fantasy");
  const [theme, setTheme] = useState<string>("survival, honor, and political intrigue");
  const [tone, setTone] = useState<string>("grounded, gritty, and atmospheric");
  const [length, setLength] = useState<CampaignLength>("medium");
  const [difficulty, setDifficulty] = useState<CampaignDifficulty>("normal");

  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !premise.trim()) {
      setError("Title and Premise are required.");
      return;
    }

    setSubmitting(true);
    setError(null);

    const brief: BuilderBrief = {
      title: title.trim(),
      premise: premise.trim(),
      campaign_mode: campaignMode,
      custom_prompt: customPrompt.trim() ? customPrompt.trim() : null,
      genre: genre.trim(),
      theme: theme.trim(),
      tone: tone.trim(),
      length,
      difficulty,
    };

    try {
      const draft = await defaultApiClient.createGuidedDraft(brief);
      navigate(`/builder/drafts/${draft.draft_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create draft");
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      aria-label="Guided Campaign Brief Form"
      style={{
        maxWidth: "800px",
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        gap: "1.5rem",
      }}
    >
      <BuilderNav />
      <div>
        <h1 style={{ marginBottom: "0.5rem" }}>Guided Campaign Builder</h1>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
          Define the parameters for your custom campaign world. All generation happens locally
          using your configured Ollama model.
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

      {/* Local-only notice */}
      <div
        style={{
          padding: "var(--space-3)",
          backgroundColor: "var(--color-bg-elevated)",
          borderRadius: "var(--radius-md)",
          fontSize: "var(--font-size-xs)",
          color: "var(--color-text-muted)",
        }}
      >
        🔒 Local Privacy Notice: All source text and generation prompts are processed
        strictly on your local machine and never sent over the network.
      </div>

      {/* Title */}
      <div>
        <label
          htmlFor="brief-title"
          style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
        >
          Campaign Title <span style={{ color: "var(--color-danger)" }}>*</span>
        </label>
        <input
          id="brief-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. The Sunken Spire"
          required
          maxLength={100}
        />
      </div>

      {/* Premise */}
      <div>
        <label
          htmlFor="brief-premise"
          style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
        >
          World Premise & Lore <span style={{ color: "var(--color-danger)" }}>*</span>
        </label>
        <textarea
          id="brief-premise"
          rows={5}
          value={premise}
          onChange={(e) => setPremise(e.target.value)}
          placeholder="Describe the world, factions, conflicts, and starting situation..."
          required
          maxLength={4000}
        />
      </div>

      {/* Mode & Prompt */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div>
          <label
            htmlFor="brief-mode"
            style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
          >
            Campaign Mode
          </label>
          <select
            id="brief-mode"
            value={campaignMode}
            onChange={(e) => setCampaignMode(e.target.value as CampaignMode)}
          >
            <option value="llm_decide">LLM Decide (Autonomous Worldbuilding)</option>
            <option value="faithful_story">Faithful Story (Follow Book Lore)</option>
            <option value="custom_prompt">Custom Story Prompt</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="brief-genre"
            style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
          >
            Genre
          </label>
          <input
            id="brief-genre"
            type="text"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            maxLength={100}
          />
        </div>
      </div>

      {/* Custom Prompt */}
      {campaignMode !== "llm_decide" && (
        <div>
          <label
            htmlFor="brief-custom-prompt"
            style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
          >
            Custom Narrative Directive / Focus
          </label>
          <textarea
            id="brief-custom-prompt"
            rows={3}
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="Specific characters to include, plot beats to hit, or regional lore..."
            maxLength={4000}
          />
        </div>
      )}

      {/* Theme & Tone */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div>
          <label
            htmlFor="brief-theme"
            style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
          >
            Theme
          </label>
          <input
            id="brief-theme"
            type="text"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            maxLength={200}
          />
        </div>

        <div>
          <label
            htmlFor="brief-tone"
            style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
          >
            Tone
          </label>
          <input
            id="brief-tone"
            type="text"
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            maxLength={200}
          />
        </div>
      </div>

      {/* Length & Difficulty */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div>
          <label
            htmlFor="brief-length"
            style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
          >
            Campaign Scope / Length
          </label>
          <select
            id="brief-length"
            value={length}
            onChange={(e) => setLength(e.target.value as CampaignLength)}
          >
            <option value="short">Short (3-5 areas, focused adventure)</option>
            <option value="medium">Medium (6-12 areas, standard campaign)</option>
            <option value="long">Long (15+ areas, epic campaign)</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="brief-difficulty"
            style={{ display: "block", fontWeight: "600", marginBottom: "0.25rem" }}
          >
            Difficulty
          </label>
          <select
            id="brief-difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as CampaignDifficulty)}
          >
            <option value="story">Story (Forgiving checks, lower enemy damage)</option>
            <option value="normal">Normal (Standard balanced rules)</option>
            <option value="hard">Hard (Brutal combat, high stakes)</option>
          </select>
        </div>
      </div>

      {/* Submit */}
      <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
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
          {submitting ? "Creating Draft..." : "Initialize Campaign Draft →"}
        </button>
      </div>
    </form>
  );
}
