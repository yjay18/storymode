import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import type { DraftStage, DraftState, ValidationReport } from "../../api/schema";
import { GenerationProgress } from "./GenerationProgress";
import { PublishModal } from "./PublishModal";
import { ValidationReportView } from "./ValidationReportView";

export function DraftWorkspace(): React.JSX.Element {
  const { draftId } = useParams<{ draftId: string }>();
  const navigate = useNavigate();

  const [draft, setDraft] = useState<DraftState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [valReport, setValReport] = useState<ValidationReport | null>(null);
  const [valLoading, setValLoading] = useState<boolean>(false);

  const [showPublishModal, setShowPublishModal] = useState<boolean>(false);
  const [publishing, setPublishing] = useState<boolean>(false);
  const [publishError, setPublishError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDraft = async () => {
      if (!draftId) return;
      setLoading(true);
      setError(null);
      try {
        const d = await defaultApiClient.getDraft(draftId);
        setDraft(d);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load draft");
      } finally {
        setLoading(false);
      }
    };

    fetchDraft();
  }, [draftId]);

  const handleGenerate = async (stage?: DraftStage) => {
    if (!draftId) return;
    setGenerating(true);
    setError(null);
    try {
      const updated = await defaultApiClient.generateDraftStage(draftId, stage);
      setDraft(updated);
      await fetchValidation();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleCancel = async () => {
    if (!draftId) return;
    try {
      const updated = await defaultApiClient.cancelDraft(draftId);
      setDraft(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    } finally {
      setGenerating(false);
    }
  };

  const fetchValidation = async () => {
    if (!draftId) return;
    setValLoading(true);
    try {
      const report = await defaultApiClient.validateDraft(draftId);
      setValReport(report);
    } catch {
      // Ignored
    } finally {
      setValLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!draftId) return;
    setPublishing(true);
    setPublishError(null);
    try {
      const res = await defaultApiClient.publishDraft(draftId, true);
      navigate(`/campaigns/${res.campaign_id}`);
    } catch (err) {
      setPublishError(err instanceof Error ? err.message : "Publishing failed");
      setPublishing(false);
    }
  };

  if (loading) {
    return (
      <section aria-label="Draft Workspace">
        <p style={{ color: "var(--color-text-secondary)" }}>Loading campaign draft...</p>
      </section>
    );
  }

  if (error || !draft) {
    return (
      <section aria-label="Draft Workspace">
        <h1 style={{ color: "var(--color-danger)", marginBottom: "1rem" }}>Error Loading Draft</h1>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>{error}</p>
        <Link to="/" style={{ color: "var(--color-accent)" }}>
          ← Return to Library
        </Link>
      </section>
    );
  }

  return (
    <section aria-label="Draft Workspace">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <Link to="/" style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-sm)" }}>
            ← Back to Library
          </Link>
          <h1 style={{ marginTop: "0.25rem" }}>{draft.brief.title}</h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
            Draft ID: {draft.draft_id} • Revision: {draft.revision}
          </p>
        </div>

        <div>
          {draft.is_published ? (
            <span
              style={{
                padding: "var(--space-2) var(--space-4)",
                backgroundColor: "rgba(52, 211, 153, 0.15)",
                color: "var(--color-success)",
                fontWeight: "bold",
                borderRadius: "var(--radius-md)",
              }}
            >
              ✓ Published ({draft.published_campaign_id})
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setShowPublishModal(true)}
              style={{
                backgroundColor: "var(--color-success)",
                color: "var(--color-bg-base)",
                fontWeight: "bold",
                padding: "var(--space-2) var(--space-4)",
              }}
            >
              Publish Campaign Pack →
            </button>
          )}
        </div>
      </div>

      {/* Premise Box */}
      <div
        style={{
          padding: "var(--space-3)",
          backgroundColor: "var(--color-bg-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-md)",
          marginBottom: "1.5rem",
          fontSize: "var(--font-size-sm)",
          color: "var(--color-text-secondary)",
        }}
      >
        <strong>Premise:</strong> {draft.brief.premise}
      </div>

      <GenerationProgress
        stages={draft.stages}
        generating={generating}
        onGenerate={handleGenerate}
        onCancel={handleCancel}
      />

      <ValidationReportView
        report={valReport}
        loading={valLoading}
        onRefresh={fetchValidation}
      />

      <PublishModal
        isOpen={showPublishModal}
        publishing={publishing}
        error={publishError}
        onConfirm={handlePublish}
        onClose={() => setShowPublishModal(false)}
      />
    </section>
  );
}
