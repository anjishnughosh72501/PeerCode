import { forwardRef, useRef, useState } from "react";
import { m, useAnimationControls, useMotionValue, useReducedMotion, useSpring } from "motion/react";

const VARIANTS = {
  primary:
    "text-[var(--on-accent)] bg-[linear-gradient(180deg,var(--accent-strong),var(--color-accent))] shadow-[0_6px_24px_var(--glow)] hover:shadow-[0_8px_32px_var(--glow-strong)]",
  secondary: "glass text-[var(--color-ink)] hover:bg-white/10",
  danger:
    "bg-red-500/15 border border-red-400/30 text-red-200 hover:bg-red-500/25 hover:shadow-[0_4px_20px_rgba(239,68,68,0.25)]",
  ghost: "text-muted hover:text-[var(--color-ink)]",
};

const GlassButton = forwardRef(function GlassButton(
  { variant = "secondary", children, className = "", onClick, disabled = false, ...rest },
  ref
) {
  const reduceMotion = useReducedMotion();
  const controls = useAnimationControls();
  const [ripples, setRipples] = useState([]);
  const rippleId = useRef(0);

  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const x = useSpring(mx, { stiffness: 300, damping: 24 });
  const y = useSpring(my, { stiffness: 300, damping: 24 });

  const magnetic = variant === "primary" && !reduceMotion;

  function handleMove(e) {
    if (!magnetic) return;
    const r = e.currentTarget.getBoundingClientRect();
    mx.set(Math.max(-3, Math.min(3, (e.clientX - r.left - r.width / 2) * 0.08)));
    my.set(Math.max(-3, Math.min(3, (e.clientY - r.top - r.height / 2) * 0.08)));
  }

  function handleLeave() {
    mx.set(0);
    my.set(0);
  }

  function addRipple(e) {
    if (reduceMotion) return;
    const r = e.currentTarget.getBoundingClientRect();
    const id = ++rippleId.current;
    setRipples((rs) => [...rs, { id, x: e.clientX - r.left, y: e.clientY - r.top }]);
  }

  function removeRipple(id) {
    setRipples((rs) => rs.filter((r) => r.id !== id));
  }

  async function handleClick(e) {
    if (!reduceMotion) {
      controls.start({ scale: [1, 0.96, 1], transition: { duration: 0.18 } });
    }
    onClick?.(e);
  }

  return (
    <m.button
      ref={ref}
      style={magnetic ? { x, y } : undefined}
      animate={controls}
      whileHover={disabled || reduceMotion ? undefined : { scale: 1.02 }}
      whileTap={disabled || reduceMotion ? undefined : { scale: 0.96 }}
      transition={{ type: "spring", stiffness: 380, damping: 22 }}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      onPointerDown={addRipple}
      onClick={handleClick}
      disabled={disabled}
      className={`relative overflow-hidden rounded-2xl px-5 py-2.5 text-sm font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
      {...rest}
    >
      {ripples.map((r) => (
        <m.span
          key={r.id}
          className="pointer-events-none absolute h-16 w-16 rounded-full bg-current opacity-30"
          style={{ left: r.x - 32, top: r.y - 32 }}
          initial={{ scale: 0, opacity: 0.35 }}
          animate={{ scale: 2.6, opacity: 0 }}
          transition={{ duration: 0.45, ease: "easeOut" }}
          onAnimationComplete={() => removeRipple(r.id)}
        />
      ))}
      <span className="relative z-10 inline-flex items-center justify-center gap-2">{children}</span>
    </m.button>
  );
});

export default GlassButton;
