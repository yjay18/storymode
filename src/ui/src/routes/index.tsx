import React from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "../components/AppShell";

export function LibraryScreen(): React.JSX.Element {
  return (
    <section aria-labelledby="library-heading">
      <h1 id="library-heading">Campaign Library</h1>
      <p style={{ color: "var(--color-text-secondary)", marginTop: "0.5rem" }}>
        Select a campaign to play or create a new world.
      </p>
    </section>
  );
}

export function GuidedBuilderScreen(): React.JSX.Element {
  return (
    <section aria-labelledby="guided-builder-heading">
      <h1 id="guided-builder-heading">Guided Campaign Builder</h1>
      <p style={{ color: "var(--color-text-secondary)", marginTop: "0.5rem" }}>
        Craft a campaign world step by step from a comprehensive brief or book text.
      </p>
    </section>
  );
}

export function QuickBuilderScreen(): React.JSX.Element {
  return (
    <section aria-labelledby="quick-builder-heading">
      <h1 id="quick-builder-heading">Quick Prompt Builder</h1>
      <p style={{ color: "var(--color-text-secondary)", marginTop: "0.5rem" }}>
        Generate a campaign world quickly from a single premise.
      </p>
    </section>
  );
}

export function CampaignDetailScreen(): React.JSX.Element {
  return (
    <section aria-labelledby="campaign-detail-heading">
      <h1 id="campaign-detail-heading">Campaign Details</h1>
      <p style={{ color: "var(--color-text-secondary)", marginTop: "0.5rem" }}>
        View campaign synopsis, characters, and save slots.
      </p>
    </section>
  );
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
        <Route path="/builder" element={<Navigate to="/builder/guided" replace />} />
        <Route path="/campaigns/:campaignId" element={<CampaignDetailScreen />} />
        <Route path="/play/:campaignId/:saveId" element={<PlayScreen />} />
        <Route path="/recovery" element={<RecoveryScreen />} />
        <Route path="*" element={<NotFoundScreen />} />
      </Routes>
    </AppShell>
  );
}
