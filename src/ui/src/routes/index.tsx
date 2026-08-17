import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import { defaultApiClient } from "../api/client";
import type { CampaignSummary, HealthResponse } from "../api/schema";
import { AppShell } from "../components/AppShell";
import { BriefForm } from "../features/builder/BriefForm";
import { DraftWorkspace } from "../features/builder/DraftWorkspace";
import { QuickPromptForm } from "../features/builder/QuickPromptForm";
import { CampaignDetail } from "../features/campaigns/CampaignDetail";
import { CampaignList } from "../features/campaigns/CampaignList";
import { PreflightCard } from "../features/startup/PreflightCard";

export function LibraryScreen(): React.JSX.Element {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState<boolean>(true);
  const [campaignsError, setCampaignsError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const h = await defaultApiClient.getHealth();
      setHealth(h);
    } catch (e) {
      setHealthError(e instanceof Error ? e.message : "Health check failed");
    } finally {
      setHealthLoading(false);
    }
  };

  const fetchCampaigns = async () => {
    setCampaignsLoading(true);
    setCampaignsError(null);
    try {
      const list = await defaultApiClient.listCampaigns();
      setCampaigns(list);
    } catch (e) {
      setCampaignsError(e instanceof Error ? e.message : "Failed to load campaigns");
    } finally {
      setCampaignsLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchCampaigns();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <PreflightCard
        health={health}
        loading={healthLoading}
        error={healthError}
        onRetry={fetchHealth}
      />
      <CampaignList
        campaigns={campaigns}
        loading={campaignsLoading}
        error={campaignsError}
        onRetry={fetchCampaigns}
      />
    </div>
  );
}

export function GuidedBuilderScreen(): React.JSX.Element {
  return <BriefForm />;
}

export function QuickBuilderScreen(): React.JSX.Element {
  return <QuickPromptForm />;
}

export function CampaignDetailScreen(): React.JSX.Element {
  return <CampaignDetail />;
}

export function PlayScreen(): React.JSX.Element {
  return (
    <section aria-labelledby="play-heading">
      <h1 id="play-heading">Active Adventure</h1>
      <p style={{ color: "var(--color-text-secondary)", marginTop: "0.5rem" }}>
        Explore the realm and engage in tactical encounters.
      </p>
    </section>
  );
}

export function RecoveryScreen(): React.JSX.Element {
  return (
    <section aria-labelledby="recovery-heading">
      <h1 id="recovery-heading">Save Recovery</h1>
      <p style={{ color: "var(--color-text-secondary)", marginTop: "0.5rem" }}>
        Diagnose and restore corrupted or orphaned save files from snapshots.
      </p>
    </section>
  );
}

export function NotFoundScreen(): React.JSX.Element {
  return (
    <section aria-labelledby="not-found-heading" style={{ textAlign: "center", padding: "4rem 0" }}>
      <h1 id="not-found-heading" style={{ marginBottom: "1rem" }}>
        404 — Page Not Found
      </h1>
      <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>
        The requested screen does not exist.
      </p>
      <Link to="/" style={{ color: "var(--color-accent)", textDecoration: "underline" }}>
        Return to Campaign Library
      </Link>
    </section>
  );
}

export function AppRoutes(): React.JSX.Element {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<LibraryScreen />} />
        <Route path="/builder/guided" element={<GuidedBuilderScreen />} />
        <Route path="/builder/quick" element={<QuickBuilderScreen />} />
        <Route path="/builder/drafts/:draftId" element={<DraftWorkspace />} />
        <Route path="/builder" element={<Navigate to="/builder/guided" replace />} />
        <Route path="/campaigns/:campaignId" element={<CampaignDetailScreen />} />
        <Route path="/play/:campaignId/:saveId" element={<PlayScreen />} />
        <Route path="/recovery" element={<RecoveryScreen />} />
        <Route path="*" element={<NotFoundScreen />} />
      </Routes>
    </AppShell>
  );
}
