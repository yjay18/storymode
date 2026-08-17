import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("Uncaught render error:", error, errorInfo);
  }

  public handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  public override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <main
          aria-label="Application Error"
          style={{
            padding: "2rem",
            maxWidth: "600px",
            margin: "4rem auto",
            backgroundColor: "var(--color-bg-surface)",
            border: "1px solid var(--color-danger)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <h1 style={{ color: "var(--color-danger)", marginBottom: "1rem" }}>
            Something went wrong
          </h1>
          <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>
            An unexpected error occurred during rendering. Your saved game state is safe.
          </p>
          {this.state.error && (
            <pre
              style={{
                backgroundColor: "var(--color-bg-base)",
                padding: "1rem",
                borderRadius: "var(--radius-md)",
                overflowX: "auto",
                marginBottom: "1.5rem",
                fontSize: "var(--font-size-sm)",
                color: "var(--color-text-muted)",
              }}
            >
              {this.state.error.message}
            </pre>
          )}
          <button type="button" onClick={this.handleReset}>
            Try again
          </button>
        </main>
      );
    }

    return this.props.children;
  }
}
