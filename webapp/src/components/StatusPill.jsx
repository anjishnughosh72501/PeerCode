import { m } from "motion/react";

const TONES = {
  connected: { dot: "bg-emerald-400", label: "Connected" },
  connecting: { dot: "bg-accent", label: "Connecting" },
  offline: { dot: "bg-red-400", label: "Offline" },
};

export default function StatusPill({ status = "connecting", className = "" }) {
  const tone = TONES[status] ?? TONES.connecting;
  return (
    <m.span
      layout
      className={`glass inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-medium ${className}`}
    >
      <span className="relative flex h-2 w-2">
        <m.span
          className={`absolute inline-flex h-full w-full rounded-full ${tone.dot}`}
          animate={{ opacity: [0.9, 0.25, 0.9], scale: [1, 1.7, 1] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        />
        <span className={`relative inline-flex h-2 w-2 rounded-full ${tone.dot}`} />
      </span>
      {tone.label}
    </m.span>
  );
}
