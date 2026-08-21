import { AnimatePresence, m } from "motion/react";

export default function AnimatedModal({ open, onClose, children, width = "max-w-md" }) {
  return (
    <AnimatePresence>
      {open && (
        <m.div
          className="absolute inset-0 z-40 flex items-center justify-center p-8"
          initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
          animate={{ opacity: 1, backdropFilter: "blur(10px)" }}
          exit={{ opacity: 0, backdropFilter: "blur(0px)", transition: { duration: 0.18 } }}
          transition={{ duration: 0.25 }}
          style={{ background: "rgba(5,6,9,0.45)" }}
          onClick={onClose}
        >
          <m.div
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
            initial={{ opacity: 0, scale: 0.94, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8, transition: { duration: 0.16 } }}
            transition={{ type: "spring", stiffness: 340, damping: 26 }}
            className={`glass card-shadow noise relative w-full ${width} rounded-[22px] p-7`}
          >
            {children}
          </m.div>
        </m.div>
      )}
    </AnimatePresence>
  );
}
