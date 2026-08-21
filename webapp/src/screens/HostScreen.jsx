import { useState } from "react";
import { m, useReducedMotion } from "motion/react";
import GlassButton from "../components/GlassButton.jsx";
import GlassInput from "../components/GlassInput.jsx";
import { api } from "../api.js";
import { useToast } from "../components/Toast.jsx";

export default function HostScreen({ onBack, onHosted }) {
  const toast = useToast();
  const reduceMotion = useReducedMotion();
  const [name, setName] = useState("Host");
  const [filepath, setFilepath] = useState("");
  const [busy, setBusy] = useState(false);
  const [browsing, setBrowsing] = useState(false);
  const [error, setError] = useState("");

  async function browse() {
    setBrowsing(true);
    try {
      const res = await api.pickFolder();
      if (res.path) {
        setFilepath(res.path);
        setError("");
      }
    } catch {
      toast({ tone: "error", title: "Could not open folder picker" });
    } finally {
      setBrowsing(false);
    }
  }

  async function start() {
    if (!filepath.trim()) {
      setError("Please enter a project folder path.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const info = await api.hostSession(name.trim() || "Host", filepath.trim());
      onHosted({ ...info, role: "host", name: name.trim() || "Host" });
    } catch (e) {
      setError(e.message || "Could not start hosting.");
      toast({ tone: "error", title: "Hosting failed", message: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <m.div
      initial={{ opacity: 0, y: 14, filter: "blur(6px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      exit={{ opacity: 0, y: -10, transition: { duration: 0.18 } }}
      transition={{ type: "spring", stiffness: 260, damping: 26 }}
      className="flex h-full items-center justify-center px-10"
    >
      <div className="glass card-shadow noise w-full max-w-md rounded-[22px] p-9">
        <button onClick={onBack} className="text-muted mb-6 text-sm transition-colors hover:text-[var(--color-ink)]">
          &larr; Back
        </button>
        <h1 className="font-display text-3xl font-semibold">Host a session</h1>
        <p className="text-muted mt-2 text-sm">
          Share a project folder from this machine over your local network.
        </p>

        <div className="mt-8 flex flex-col gap-5">
          <GlassInput
            label="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Host"
          />
          <div>
            <span className="text-muted mb-2 block text-xs font-medium uppercase tracking-widest">
              Project folder
            </span>
            <div className="flex items-end gap-2">
              <GlassInput
                value={filepath}
                onChange={(e) => setFilepath(e.target.value)}
                placeholder="C:\Users\You\Projects\MyApp"
                error={!!error && !filepath.trim()}
                className="flex-1"
              />
              <GlassButton variant="secondary" onClick={browse} disabled={browsing} className="shrink-0 py-3">
                {browsing ? "Opening..." : "Browse..."}
              </GlassButton>
            </div>
          </div>
          {error && <p className="text-sm text-red-300">{error}</p>}
          <GlassButton variant="primary" onClick={start} disabled={busy} className="mt-1 w-full py-3">
            {busy ? "Starting..." : "Start Hosting"}
          </GlassButton>
        </div>
      </div>
    </m.div>
  );
}
