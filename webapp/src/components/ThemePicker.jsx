import { useState } from "react";
import { AnimatePresence, m } from "motion/react";
import Icon from "./Icon.jsx";
import { THEMES } from "../themes.js";

export default function ThemePicker({ theme, onSelect, className = "" }) {
  const [open, setOpen] = useState(false);
  const current = THEMES.find((t) => t.id === theme) ?? THEMES[0];

  return (
    <span className={`relative ${className}`}>
      <button
        onClick={() => setOpen((v) => !v)}
        title="Theme"
        className="text-muted flex items-center gap-2 rounded-xl p-2 transition-colors hover:bg-white/10 hover:text-[var(--color-ink)]"
      >
        <Icon name={current.id === "daylight" ? "sun" : "moon"} size={16} />
        <span
          className="hidden h-3.5 w-3.5 rounded-full border border-white/20 sm:block"
          style={{ background: current.accent }}
        />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <span className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
            <m.span
              initial={{ opacity: 0, y: -6, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.97, transition: { duration: 0.14 } }}
              transition={{ type: "spring", stiffness: 380, damping: 28 }}
              className="glass card-shadow absolute right-0 z-50 mt-2 flex w-44 flex-col gap-1 rounded-2xl p-2"
            >
              {THEMES.map((t) => (
                <button
                  key={t.id}
                  onClick={() => {
                    onSelect(t.id);
                    setOpen(false);
                  }}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors ${
                    t.id === theme ? "glass-bright" : "hover:bg-white/5"
                  }`}
                >
                  <span className="flex overflow-hidden rounded-full border border-white/20">
                    <span className="h-4 w-2.5" style={{ background: t.bg }} />
                    <span className="h-4 w-2.5" style={{ background: t.accent }} />
                  </span>
                  <span className="flex-1 text-left">{t.name}</span>
                  {t.id === theme && <Icon name="check" size={13} className="text-accent" />}
                </button>
              ))}
            </m.span>
          </>
        )}
      </AnimatePresence>
    </span>
  );
}
