/**
 * Command ID generation and idempotent retry tracker (UI-02).
 */

export function generateCommandId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "cmd-" + Math.random().toString(36).substring(2, 15);
}

export interface CommandTracker {
  getOrGenerate(intentKey: string): string;
  consume(intentKey: string): void;
  clear(): void;
}

export function createCommandTracker(): CommandTracker {
  const activeCommands = new Map<string, string>();

  return {
    getOrGenerate(intentKey: string): string {
      const existing = activeCommands.get(intentKey);
      if (existing) {
        return existing;
      }
      const newId = generateCommandId();
      activeCommands.set(intentKey, newId);
      return newId;
    },
    consume(intentKey: string): void {
      activeCommands.delete(intentKey);
    },
    clear(): void {
      activeCommands.clear();
    },
  };
}
