import { createContext, useCallback, useContext, useRef, useState } from "react";
import { AnimatePresence, m } from "motion/react";

const ToastContext = createContext(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idRef = useRef(0);

  const push = useCallback((toast) => {
    const id = ++idRef.current;
    setToasts((ts) => [...ts.slice(-3), { id, tone: "info", ...toast }]);
    setTimeout(() => setToasts((ts) => ts.filter((t) => t.id !== id)), toast.duration ?? 3200);
  }, []);

  const tones = {
    info: "glass",
    success: "border-emerald-400/30 shadow-[0_8px_28px_rgba(52,211,153,0.15)]",
    error: "border-red-400/30 shadow-[0_8px_28px_rgba(239,68,68,0.15)]",
  };

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none absolute right-5 top-5 z-50 flex w-72 flex-col gap-2">
        <AnimatePresence>
          {toasts.map((t) => (
            <m.div
              key={t.id}
              layout
              initial={{ opacity: 0, x: 24, y: -12, filter: "blur(6px)" }}
              animate={{ opacity: 1, x: 0, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, x: 16, scale: 0.96, transition: { duration: 0.18 } }}
              transition={{ type: "spring", stiffness: 340, damping: 26 }}
              className={`glass pointer-events-auto rounded-2xl px-4 py-3 text-sm ${tones[t.tone] || tones.info}`}
            >
              {t.title && <div className="font-medium">{t.title}</div>}
              {t.message && <div className="text-muted mt-0.5 text-xs">{t.message}</div>}
            </m.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
