import { useCallback, useEffect, useState } from "react";
import { LazyMotion, domAnimation, AnimatePresence, m } from "motion/react";
import { ToastProvider } from "./components/Toast.jsx";
import AmbientBackground from "./components/AmbientBackground.jsx";
import LaunchScreen from "./screens/LaunchScreen.jsx";
import HostScreen from "./screens/HostScreen.jsx";
import JoinScreen from "./screens/JoinScreen.jsx";
import WorkspaceScreen from "./screens/WorkspaceScreen.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { DEFAULT_THEME } from "./themes.js";

export default function App() {
  const [screen, setScreen] = useState("launch");
  const [session, setSession] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem("peercode-theme") || DEFAULT_THEME);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("peercode-theme", theme);
  }, [theme]);

  const changeTheme = useCallback((id) => setTheme(id), []);

  const exitWorkspace = useCallback(() => {
    setSession(null);
    setScreen("launch");
  }, []);

  return (
    <LazyMotion features={domAnimation} strict>
      <ToastProvider>
        <ErrorBoundary>
        <div className="relative h-full w-full p-4">
          <AmbientBackground />

          {/* frameless rounded window */}
          <div
            className="card-shadow relative h-full w-full overflow-hidden rounded-[18px] border"
            style={{ borderColor: "var(--border)", background: "rgba(9,11,15,0.55)", backdropFilter: "blur(28px)" }}
          >
            <AnimatePresence mode="wait">
              {screen === "launch" && (
                <m.div key="launch" className="h-full">
                  <LaunchScreen onHost={() => setScreen("host-setup")} onJoin={() => setScreen("join-setup")} />
                </m.div>
              )}
              {screen === "host-setup" && (
                <m.div key="host-setup" className="h-full">
                  <HostScreen onBack={() => setScreen("launch")} onHosted={(s) => { setSession(s); setScreen("workspace"); }} />
                </m.div>
              )}
              {screen === "join-setup" && (
                <m.div key="join-setup" className="h-full">
                  <JoinScreen onBack={() => setScreen("launch")} onJoined={(s) => { setSession(s); setScreen("workspace"); }} />
                </m.div>
              )}
              {screen === "workspace" && session && (
                <m.div key="workspace" className="h-full">
                  <WorkspaceScreen
                    session={session}
                    theme={theme}
                    onSetTheme={changeTheme}
                    onExit={exitWorkspace}
                  />
                </m.div>
              )}
            </AnimatePresence>
          </div>
        </div>
        </ErrorBoundary>
      </ToastProvider>
    </LazyMotion>
  );
}
