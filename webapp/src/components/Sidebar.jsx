import { AnimatePresence, m } from "motion/react";
import Icon from "./Icon.jsx";

const ITEMS = [
  { id: "session", icon: "session", label: "Session" },
  { id: "files", icon: "files", label: "Files" },
  { id: "members", icon: "users", label: "Members" },
  { id: "settings", icon: "settings", label: "Settings" },
];

export default function Sidebar({ active, onSelect, expanded = false, onToggle, logo = "PeerCode" }) {
  return (
    <m.aside
      layout
      initial={false}
      animate={{ width: expanded ? 232 : 72 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="glass z-10 flex h-full flex-col overflow-hidden rounded-[18px] p-3"
    >
      <button
        onClick={onToggle}
        title={expanded ? "Collapse" : "Expand"}
        className="mb-5 flex items-center gap-3 rounded-xl px-1.5 py-1 text-left"
      >
        <span className="accent-solid accent-glow flex h-9 w-9 shrink-0 items-center justify-center rounded-xl font-display text-lg font-bold">
          P
        </span>
        <AnimatePresence initial={false}>
          {expanded && (
            <m.span
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -6 }}
              transition={{ duration: 0.18 }}
              className="font-display whitespace-nowrap text-lg font-semibold tracking-wide"
            >
              {logo}
            </m.span>
          )}
        </AnimatePresence>
      </button>

      <nav className="flex flex-col gap-1.5">
        {ITEMS.map((item) => {
          const isActive = item.id === active;
          return (
            <button
              key={item.id}
              onClick={() => onSelect(item.id)}
              title={item.label}
              className={`relative flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm transition-colors duration-200 ${
                isActive ? "text-[var(--color-ink)]" : "text-muted hover:text-[var(--color-ink)]"
              }`}
            >
              {isActive && (
                <m.span
                  layoutId="sidebar-active"
                  className="glass-bright absolute inset-0 rounded-2xl border border-white/10"
                  transition={{ type: "spring", stiffness: 380, damping: 32 }}
                />
              )}
              <span className="relative z-10 flex w-6 shrink-0 justify-center">
                <Icon name={item.icon} />
              </span>
              <AnimatePresence initial={false}>
                {expanded && (
                  <m.span
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -6 }}
                    transition={{ duration: 0.18 }}
                    className="relative z-10 whitespace-nowrap"
                  >
                    {item.label}
                  </m.span>
                )}
              </AnimatePresence>
            </button>
          );
        })}
      </nav>

      <div className="mt-auto flex justify-center pb-1">
        <span className="text-[9px] uppercase tracking-widest text-muted opacity-50 [writing-mode:vertical-rl]">
          LAN session
        </span>
      </div>
    </m.aside>
  );
}
