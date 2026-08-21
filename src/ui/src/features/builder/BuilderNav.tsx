import React from "react";
import { Link, useLocation } from "react-router-dom";

export function BuilderNav(): React.JSX.Element {
  const location = useLocation();
  const currentPath = location.pathname;

  const links = [
    { path: "/builder/guided", label: "Guided Form" },
    { path: "/builder/quick", label: "Quick Prompt" },
    { path: "/builder/import", label: "📖 Drop EPUB / Book" },
  ];

  return (
    <nav
      aria-label="Builder Creation Modes"
      style={{
        display: "flex",
        gap: "0.5rem",
        marginBottom: "1.5rem",
        borderBottom: "1px solid var(--color-border-subtle)",
        paddingBottom: "0.75rem",
      }}
    >
      {links.map((link) => {
        const isActive = currentPath === link.path;
        return (
          <Link
            key={link.path}
            to={link.path}
            style={{
              padding: "var(--space-2) var(--space-4)",
              borderRadius: "var(--radius-md)",
              backgroundColor: isActive ? "var(--color-bg-elevated)" : "transparent",
              color: isActive ? "var(--color-text-primary)" : "var(--color-text-secondary)",
              fontWeight: isActive ? 600 : 400,
              textDecoration: "none",
              border: isActive ? "1px solid var(--color-border-subtle)" : "1px solid transparent",
            }}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
