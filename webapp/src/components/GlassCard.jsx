import { m } from "motion/react";

const cardVariants = {
  hidden: { opacity: 0, y: 14, filter: "blur(8px)" },
  show: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { type: "spring", stiffness: 260, damping: 26 },
  },
};

export default function GlassCard({ children, className = "", interactive = false, onClick, ...rest }) {
  const interaction = interactive
    ? {
        whileHover: { y: -6, scale: 1.01 },
        whileTap: { scale: 0.96 },
        transition: { type: "spring", stiffness: 320, damping: 22 },
      }
    : {};
  return (
    <m.div
      variants={cardVariants}
      className={`glass card-shadow rounded-[22px] ${interactive ? "cursor-pointer hover:border-white/25" : ""} ${className}`}
      onClick={onClick}
      {...interaction}
      {...rest}
    >
      {children}
    </m.div>
  );
}

export { cardVariants };
