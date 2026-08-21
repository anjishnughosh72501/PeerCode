import { m } from "motion/react";

export default function AmbientBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <m.div
        className="absolute -left-32 -top-40 h-[480px] w-[480px] rounded-full opacity-[0.10]"
        style={{ background: "radial-gradient(circle, var(--blob1) 0%, transparent 65%)", filter: "blur(60px)" }}
        animate={{ x: [0, 50, 0], y: [0, 30, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />
      <m.div
        className="absolute -bottom-48 -right-32 h-[520px] w-[520px] rounded-full opacity-[0.08]"
        style={{ background: "radial-gradient(circle, var(--blob2) 0%, transparent 65%)", filter: "blur(70px)" }}
        animate={{ x: [0, -40, 0], y: [0, -36, 0] }}
        transition={{ duration: 32, repeat: Infinity, ease: "easeInOut" }}
      />
      <m.div
        className="absolute left-1/3 top-1/4 h-[380px] w-[380px] rounded-full opacity-[0.07]"
        style={{ background: "radial-gradient(circle, var(--blob3) 0%, transparent 60%)", filter: "blur(80px)" }}
        animate={{ x: [0, 30, -20, 0], y: [0, -24, 16, 0] }}
        transition={{ duration: 38, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}
