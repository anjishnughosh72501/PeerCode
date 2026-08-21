import { forwardRef } from "react";

const GlassInput = forwardRef(function GlassInput(
  { label, error = false, className = "", inputClassName = "", ...rest },
  ref
) {
  return (
    <label className={`block ${className}`}>
      {label ? (
        <span className="mb-2 block text-xs font-medium uppercase tracking-widest text-muted">{label}</span>
      ) : null}
      <span
        className={`glass block rounded-2xl px-4 py-3 transition-shadow duration-200 focus-within:shadow-[0_0_0_1px_var(--glow),0_4px_20px_var(--glow)] ${
          error ? "border-red-400/60 shadow-[0_0_0_1px_rgba(248,113,113,0.4)]" : ""
        }`}
      >
        <input ref={ref} className="glass-input-field text-sm" {...rest} />
      </span>
    </label>
  );
});

export default GlassInput;
