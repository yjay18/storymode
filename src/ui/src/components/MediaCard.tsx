import React, { useState } from "react";

export interface FallbackCardData {
  entity_type: "cover" | "area_background" | "enemy_portrait";
  entity_id: string;
  title: string;
  accent_color: string;
  bg_gradient_start: string;
  bg_gradient_end: string;
  icon_symbol: string;
  accessible_description: string;
}

interface MediaCardProps {
  imageUrl?: string | null;
  accessibleAlt: string;
  fallbackData: FallbackCardData;
  height?: string;
}

export function MediaCard({
  imageUrl,
  accessibleAlt,
  fallbackData,
  height = "160px",
}: MediaCardProps): React.JSX.Element {
  const [imageFailed, setImageFailed] = useState<boolean>(false);

  if (imageUrl && !imageFailed) {
    return (
      <div
        style={{
          width: "100%",
          height,
          borderRadius: "var(--radius-lg)",
          overflow: "hidden",
          backgroundColor: "var(--color-bg-elevated)",
          position: "relative",
          marginBottom: "1rem",
        }}
      >
        <img
          src={imageUrl}
          alt={accessibleAlt}
          loading="lazy"
          onError={() => setImageFailed(true)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
          }}
        />
      </div>
    );
  }

  // Render deterministic themed fallback card
  return (
    <div
      role="img"
      aria-label={fallbackData.accessible_description}
      style={{
        width: "100%",
        height,
        borderRadius: "var(--radius-lg)",
        background: `linear-gradient(135deg, ${fallbackData.bg_gradient_start}, ${fallbackData.bg_gradient_end})`,
        border: `1px solid ${fallbackData.accent_color}44`,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "1rem",
        textAlign: "center",
        marginBottom: "1rem",
        boxShadow: "inset 0 0 20px rgba(0,0,0,0.5)",
      }}
    >
      <div style={{ fontSize: "2.5rem", marginBottom: "0.25rem" }}>
        {fallbackData.icon_symbol}
      </div>
      <strong style={{ fontSize: "var(--font-size-md)", color: "var(--color-text-primary)" }}>
        {fallbackData.title}
      </strong>
      <span
        style={{
          fontSize: "var(--font-size-xs)",
          color: "var(--color-text-muted)",
          marginTop: "0.25rem",
          textTransform: "capitalize",
        }}
      >
        {fallbackData.entity_type.replace("_", " ")}
      </span>
    </div>
  );
}
