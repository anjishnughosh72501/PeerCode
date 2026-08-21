import { useEffect, useRef, useState } from "react";
import { m, useAnimationControls, useReducedMotion } from "motion/react";
import GlassButton from "../components/GlassButton.jsx";
import GlassInput from "../components/GlassInput.jsx";
import { api } from "../api.js";
import { useToast } from "../components/Toast.jsx";

export default function JoinScreen({ onBack, onJoined }) {
  const toast = useToast();
  const reduceMotion = useReducedMotion();
  const [name, setName] = useState("Guest");
  const [ip, setIp] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [discovered, setDiscovered] = useState([]);
  const shakeControls = useAnimationControls();
  const pulseControls = useAnimationControls();
  const joinedRef = useRef(false);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const data = await api.peers();
        if (alive) setDiscovered(data.discovered || []);
      } catch {
        /* backend not reachable yet */
      }
    };
    tick();
    const id = setInterval(tick, 3000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  function fail(message) {
    setError(message);
    if (!reduceMotion) {
      shakeControls.start({
        x: [0, -9, 9, -6, 6, 0],
        transition: { duration: 0.38, ease: "easeInOut" },
      });
    }
  }

  async function join() {
    if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(ip.trim())) {
      fail("Please enter a valid host IP address.");
      return;
    }
    if (!/^[A-Z2-9]{6}$/.test(code.trim().toUpperCase())) {
      fail("Session code must be 6 characters (no O/0/I/1/L).");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.validateGuest(ip.trim(), code.trim().toUpperCase());
      if (joinedRef.current) return;
      joinedRef.current = true;
      setSuccess(true);
      if (!reduceMotion) {
        pulseControls.start({ scale: [1, 1.03, 1], transition: { duration: 0.35 } });
      }
      await api.connectGuest(name.trim() || "Guest", ip.trim(), code.trim().toUpperCase());
      onJoined({ role: "guest", name: name.trim() || "Guest", code: code.trim().toUpperCase(), ip: ip.trim() });
    } catch (e) {
      joinedRef.current = false;
      setSuccess(false);
      fail(e.message || "Could not reach the host.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <m.div
      initial={{ opacity: 0, y: 14, filter: "blur(6px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      exit={{ opacity: 0, y: -10, transition: { duration: 0.18 } }}
      transition={{ type: "spring", stiffness: 260, damping: 26 }}
      className="flex h-full items-center justify-center px-10"
    >
      <m.div animate={pulseControls} className={success ? "accent-glow rounded-[22px]" : ""}>
        <div className="glass card-shadow noise w-full max-w-md rounded-[22px] p-9">
          <button onClick={onBack} className="text-muted mb-6 text-sm transition-colors hover:text-[var(--color-ink)]">
            &larr; Back
          </button>
          <h1 className="font-display text-3xl font-semibold">Join a session</h1>
          <p className="text-muted mt-2 text-sm">Enter the host IP address and session code.</p>

          <m.div animate={shakeControls} className="mt-8 flex flex-col gap-5">
            <GlassInput label="Your name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Guest" />
            <GlassInput
              label="Host IP"
              value={ip}
              onChange={(e) => setIp(e.target.value)}
              placeholder="192.168.1.45"
              inputMode="decimal"
              error={!!error && /IP/i.test(error)}
            />
            <GlassInput
              label="Session Code"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="A7X9QP"
              maxLength={6}
              className="tracking-[0.4em] uppercase"
              error={!!error && /code/i.test(error)}
            />
          </m.div>

          {error && (
            <m.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4 text-sm text-red-300">
              {error}
            </m.p>
          )}

          <div className="mt-7 flex gap-3">
            <GlassButton variant="secondary" onClick={onBack} className="flex-1 py-3">
              Back
            </GlassButton>
            <GlassButton variant="primary" onClick={join} disabled={busy} className="flex-[2] py-3">
              {busy ? "Connecting..." : success ? "Connected" : "Join"}
            </GlassButton>
          </div>

          {discovered.length > 0 && (
            <div className="mt-8 border-t border-white/5 pt-5">
              <div className="text-muted mb-3 text-xs uppercase tracking-widest">Discovered on your network</div>
              <div className="flex flex-col gap-2">
                {discovered.slice(0, 3).map((peer) => (
                  <m.button
                    key={peer.ip}
                    layout
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    onClick={() => {
                      setIp(peer.ip);
                      setCode((peer.code || "").toUpperCase());
                    }}
                    className="glass flex items-center justify-between rounded-xl px-4 py-2.5 text-left text-sm transition-colors hover:bg-white/10"
                  >
                    <span>{peer.project_name || peer.filename || peer.name}</span>
                    <span className="text-muted text-xs">
                      {peer.ip} · {peer.code}
                    </span>
                  </m.button>
                ))}
              </div>
            </div>
          )}
        </div>
      </m.div>
    </m.div>
  );
}
