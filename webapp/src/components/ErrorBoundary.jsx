import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("PeerCode crashed:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-4 p-10 text-center">
          <h1 className="font-display text-2xl font-semibold">Something went wrong</h1>
          <pre className="text-muted max-w-lg overflow-auto rounded-xl bg-white/5 p-4 text-xs whitespace-pre-wrap">
            {String(this.state.error)}
          </pre>
          <button
            onClick={() => location.reload()}
            className="glass rounded-2xl px-6 py-2.5 text-sm transition-colors hover:bg-white/10"
          >
            Reload PeerCode
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
