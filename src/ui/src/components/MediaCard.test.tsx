import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FallbackCardData, MediaCard } from "./MediaCard";

describe("MediaCard", () => {
  const fallbackData: FallbackCardData = {
    entity_type: "area_background",
    entity_id: "crypt_1",
    title: "Forgotten Crypt",
    accent_color: "#4f46e5",
    bg_gradient_start: "#1e1b4b",
    bg_gradient_end: "#0f172a",
    icon_symbol: "🏰",
    accessible_description: "Area background for 'Forgotten Crypt'",
  };

  it("renders image when imageUrl is provided", () => {
    render(
      <MediaCard
        imageUrl="/api/v1/campaigns/c1/assets/area_background/crypt_1/raw"
        accessibleAlt="Crypt scenery"
        fallbackData={fallbackData}
      />,
    );

    const img = screen.getByRole("img", { name: "Crypt scenery" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "/api/v1/campaigns/c1/assets/area_background/crypt_1/raw");
  });

  it("renders deterministic fallback card when imageUrl is absent", () => {
    render(
      <MediaCard
        imageUrl={null}
        accessibleAlt="Crypt scenery"
        fallbackData={fallbackData}
      />,
    );

    const card = screen.getByRole("img", { name: "Area background for 'Forgotten Crypt'" });
    expect(card).toBeInTheDocument();
    expect(screen.getByText("Forgotten Crypt")).toBeInTheDocument();
    expect(screen.getByText("🏰")).toBeInTheDocument();
  });

  it("switches to fallback card when image fails to load", () => {
    render(
      <MediaCard
        imageUrl="/api/v1/invalid/broken.png"
        accessibleAlt="Broken image"
        fallbackData={fallbackData}
      />,
    );

    const img = screen.getByRole("img", { name: "Broken image" });
    fireEvent.error(img);

    expect(screen.getByText("Forgotten Crypt")).toBeInTheDocument();
    expect(screen.getByText("🏰")).toBeInTheDocument();
  });
});
