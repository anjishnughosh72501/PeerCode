import { m } from "motion/react";
import GlassCard from "../components/GlassCard.jsx";
import Icon from "../components/Icon.jsx";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.05 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 16, filter: "blur(8px)" },
  show: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { type: "spring", stiffness: 240, damping: 26 },
  },
};

export default function LaunchScreen({ onHost, onJoin }) {
  return (
    <m.div
      variants={container}
      initial="hidden"
      animate="show"
      className="flex h-full flex-col items-center justify-center px-10"
    >
      <m.div variants={fadeUp} className="mb-10 flex items-center gap-3">
        <span className="accent-solid accent-glow flex h-12 w-12 items-center justify-center rounded-2xl font-display text-2xl font-bold">
          P
        </span>
        <span className="font-display text-xl font-semibold tracking-wide">PeerCode</span>
      </m.div>

      <m.h1 variants={fadeUp} className="font-display text-center text-6xl font-semibold tracking-tight">
        Code together.
      </m.h1>
      <m.p variants={fadeUp} className="text-muted mt-4 text-base">
        Create or join a secure LAN coding session.
      </m.p>

      <div className="mt-14 grid w-full max-w-xl grid-cols-2 gap-5">
        <GlassCard interactive onClick={onHost} className="p-7">
          <span className="glass-bright mb-6 flex h-11 w-11 items-center justify-center rounded-2xl text-accent">
            <Icon name="laptop" size={20} />
          </span>
          <h2 className="font-display text-lg font-semibold">Host Session</h2>
          <p className="text-muted mt-1.5 text-sm leading-relaxed">
            Create a secure workspace on your Wi-Fi.
          </p>
        </GlassCard>

        <GlassCard interactive onClick={onJoin} className="p-7">
          <span className="glass-bright mb-6 flex h-11 w-11 items-center justify-center rounded-2xl text-accent">
            <Icon name="link" size={20} />
          </span>
          <h2 className="font-display text-lg font-semibold">Join Session</h2>
          <p className="text-muted mt-1.5 text-sm leading-relaxed">
            Enter a session code and collaborate instantly.
          </p>
        </GlassCard>
      </div>
    </m.div>
  );
}
