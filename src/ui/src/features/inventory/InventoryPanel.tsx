import React from "react";
import type { RuntimeStateResponse } from "../../api/schema";

interface InventoryPanelProps {
  runtimeState: RuntimeStateResponse;
}

export function InventoryPanel({ runtimeState }: InventoryPanelProps): React.JSX.Element {
  const { inventory } = runtimeState.player;

  return (
    <section
      aria-label="Inventory & Bag"
      style={{
        padding: "var(--space-4)",
        backgroundColor: "var(--color-bg-surface)",
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "1rem" }}>
        Bag & Equipment ({inventory.length} items)
      </h2>

      {inventory.length === 0 ? (
        <p style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-sm)" }}>
          Your inventory is empty. Discover items as you explore the world.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {inventory.map((item) => (
            <div
              key={item.item_id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "var(--space-2) var(--space-3)",
                backgroundColor: "var(--color-bg-elevated)",
                borderRadius: "var(--radius-sm)",
                fontSize: "var(--font-size-sm)",
              }}
            >
              <span>{item.item_id}</span>
              <span
                style={{
                  padding: "2px 6px",
                  backgroundColor: "var(--color-bg-hover)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--font-size-xs)",
                  color: "var(--color-text-muted)",
                }}
              >
                x{item.quantity}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
