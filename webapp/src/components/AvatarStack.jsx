import { m } from "motion/react";

const PALETTE = ["#E8B15A", "#7C84FA", "#36D399", "#EC4899", "#14B8A6", "#F97316", "#60A5FA", "#C084FC"];

export function colorForName(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

function initials(name) {
  const parts = String(name).trim().split(/\s+/);
  return ((parts[0]?.[0] || "?") + (parts[1]?.[0] || "")).toUpperCase();
}

export default function AvatarStack({ people = [], max = 5, size = 32 }) {
  const shown = people.slice(0, max);
  const rest = people.length - shown.length;
  return (
    <m.div layout className="flex items-center -space-x-2">
      {shown.map((p) => (
        <m.span
          key={p.name}
          layout
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.6, opacity: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 24 }}
          title={p.isHost ? `${p.name} (host)` : p.name}
          style={{ width: size, height: size, background: colorForName(p.name) }}
          className="flex items-center justify-center rounded-full border border-black/30 text-[11px] font-semibold text-[#14100a]"
        >
          {initials(p.name)}
        </m.span>
      ))}
      {rest > 0 && (
        <span
          style={{ width: size, height: size }}
          className="glass flex items-center justify-center rounded-full text-[10px] font-medium text-muted"
        >
          +{rest}
        </span>
      )}
    </m.div>
  );
}
