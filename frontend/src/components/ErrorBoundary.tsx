import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("UI error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-[#0a0a0c] p-8 text-center text-zinc-200">
          <h1 className="text-lg font-semibold">Something went wrong</h1>
          <p className="max-w-md text-sm text-zinc-400">{this.state.error.message}</p>
          <button
            type="button"
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm text-white"
            onClick={() => window.location.reload()}
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
