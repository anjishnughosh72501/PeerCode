import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, m } from "motion/react";
import Sidebar from "../components/Sidebar.jsx";
import GlassButton from "../components/GlassButton.jsx";
import AnimatedModal from "../components/AnimatedModal.jsx";
import GlassInput from "../components/GlassInput.jsx";
import StatusPill from "../components/StatusPill.jsx";
import ThemePicker from "../components/ThemePicker.jsx";
import AvatarStack, { colorForName } from "../components/AvatarStack.jsx";
import Icon from "../components/Icon.jsx";
import { useToast } from "../components/Toast.jsx";
import { api, connectWS, applyOp } from "../api.js";

const listVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
};
const rowVariants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 26 } },
};

function InfoRow({ label, value, onCopy }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl px-4 py-3">
      <span className="text-muted text-xs uppercase tracking-widest">{label}</span>
      <span className="flex items-center gap-2">
        <span className="font-mono text-sm">{value}</span>
        <button
          onClick={() => {
            navigator.clipboard?.writeText(String(value));
            setCopied(true);
            onCopy?.(label);
            setTimeout(() => setCopied(false), 1200);
          }}
          className="text-muted rounded-lg p-1.5 transition-colors hover:bg-white/10 hover:text-[var(--color-ink)]"
          title={`Copy ${label}`}
        >
          <Icon name={copied ? "check" : "copy"} size={14} />
        </button>
      </span>
    </div>
  );
}

export default function WorkspaceScreen({ session, theme, onSetTheme, onExit }) {
  const toast = useToast();
  const [wsStatus, setWsStatus] = useState("connecting");
  const [peers, setPeers] = useState([]);
  const [section, setSection] = useState(session.role === "guest" ? "files" : "session");
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const [active, setActive] = useState(null); // {path, content, version}
  const [saveState, setSaveState] = useState("Choose a file from the project tree");
  const [tree, setTree] = useState([]);
  const [cursors, setCursors] = useState({});
  const [expandedDirs, setExpandedDirs] = useState(new Set());
  const [modal, setModal] = useState(null); // 'end' | 'new' | {type:'rename'|'delete', path}
  const [newFileName, setNewFileName] = useState("");
  const [renameValue, setRenameValue] = useState("");
  const [caret, setCaret] = useState({ line: 1, col: 1 });
  const [requests, setRequests] = useState([]); // pending join requests (host)
  const [waitingApproval, setWaitingApproval] = useState(session.role === "guest");

  const areaRef = useRef(null);
  const linesRef = useRef(null);
  const contentRef = useRef("");
  const applyingRemote = useRef(false);
  const activeRef = useRef(null);
  activeRef.current = active;

  const myName = session.name;

  const refreshTree = useCallback(async () => {
    try {
      const data = await api.projectTree();
      setTree(data.tree || []);
    } catch {
      /* ignore */
    }
  }, []);

  // ---- websocket events -------------------------------------------------
  useEffect(() => {
    const close = connectWS(
      (event) => {
        switch (event.type) {
          case "peer_list":
            setPeers(event.peers || []);
            break;
          case "text_edit": {
            const cur = activeRef.current;
            if (!cur || event.path !== cur.path || event.author === myName) break;
            const el = areaRef.current;
            const caretAt = el ? el.selectionStart : null;
            const nextText = applyOp(contentRef.current, event.op);
            contentRef.current = nextText;
            applyingRemote.current = true;
            setActive((a) => (a && a.path === event.path ? { ...a, content: nextText } : a));
            queueMicrotask(() => {
              applyingRemote.current = false;
            });
            requestAnimationFrame(() => {
              if (el && caretAt !== null) {
                const pos = Math.min(caretAt, nextText.length);
                el.setSelectionRange(pos, pos);
              }
            });
            break;
          }
          case "active_file":
            if (event.path) {
              // Ignore echoes for the file we already have open with identical
              // content (e.g. our own openFile triggering the broadcast) —
              // otherwise typing in the first instants gets reverted.
              const curOpen = activeRef.current;
              if (
                curOpen &&
                curOpen.path === event.path &&
                (event.content || "") === contentRef.current
              ) {
                if (event.version && event.version !== curOpen.version) {
                  setActive((a) => (a ? { ...a, version: event.version } : a));
                }
                break;
              }
              contentRef.current = event.content || "";
              applyingRemote.current = true;
              setActive({ path: event.path, content: event.content || "", version: event.version || 1 });
              setSaveState(`Opened ${event.path}`);
              queueMicrotask(() => {
                applyingRemote.current = false;
              });
              refreshTree();
            }
            break;
          case "file_update":
            if (activeRef.current && event.path === activeRef.current.path) {
              // Same content (our own save echoing back): keep local state,
              // only adopt the new version — don't rewind newer keystrokes.
              if ((event.content || "") === contentRef.current) {
                setActive((a) => ({ ...a, version: event.version }));
                setSaveState(`Updated · v${event.version}`);
                break;
              }
              contentRef.current = event.content || "";
              applyingRemote.current = true;
              setActive((a) => ({ ...a, content: event.content || "", version: event.version }));
              setSaveState(`Updated · v${event.version}`);
              queueMicrotask(() => {
                applyingRemote.current = false;
              });
            }
            break;
          case "cursor_update":
            if (event.author && event.author !== myName) {
              setCursors((c) => ({
                ...c,
                [event.author]: {
                  line: event.line,
                  col: event.col,
                  color: event.color || colorForName(event.author),
                  path: event.path,
                },
              }));
            }
            break;
          case "session_closed":
            toast({ tone: "info", title: "Session ended", message: event.message });
            onExit();
            break;
          case "join_request":
            setRequests((r) =>
              r.some((x) => x.request_id === event.request_id)
                ? r
                : [...r, { request_id: event.request_id, name: event.name }]
            );
            toast({ tone: "info", title: "Join request", message: `${event.name} wants to join the session.` });
            break;
          case "join_resolved":
            setRequests((r) => r.filter((x) => x.request_id !== event.request_id));
            break;
          case "connected":
            setWaitingApproval(false);
            refreshTree();
            break;
          case "waiting_approval":
            setWaitingApproval(true);
            break;
          case "error":
            toast({ tone: "error", title: "Error", message: event.message });
            if (session.role === "guest" && /declined|removed/i.test(event.message || "")) {
              onExit();
            }
            break;
          default:
            break;
        }
      },
      setWsStatus
    );
    refreshTree();
    return close;
  }, [myName, session, onExit, refreshTree, toast]);

  // ---- editor handlers --------------------------------------------------
  function handleInput(e) {
    if (applyingRemote.current || !active) return;
    const next = e.target.value;
    const prev = contentRef.current;
    if (next === prev) return;
    const op = diffLocal(prev, next);
    contentRef.current = next;
    // keep the controlled textarea in sync with what the user typed
    setActive((a) => (a && a.path === active.path ? { ...a, content: next } : a));
    if (op) api.textEdit(active.path, op).catch(() => {});
  }

  function updateCaret() {
    const el = areaRef.current;
    if (!el) return;
    const upto = el.value.slice(0, el.selectionStart);
    const lines = upto.split("\n");
    setCaret({ line: lines.length, col: lines[lines.length - 1].length + 1 });
    if (active && !applyingRemote.current) {
      api.cursor(active.path, lines.length, lines[lines.length - 1].length + 1).catch(() => {});
    }
  }

  async function openFile(path) {
    try {
      const res = await api.readFile(path);
      api.setActiveFile(path).catch(() => {});
      contentRef.current = res.content;
      applyingRemote.current = true;
      setActive({ path, content: res.content, version: res.version });
      setSaveState(`Opened ${path} · v${res.version}`);
      queueMicrotask(() => {
        applyingRemote.current = false;
      });
    } catch (e) {
      toast({ tone: "error", title: "Cannot open file", message: e.message });
    }
  }

  async function save() {
    if (!active) return;
    try {
      const res = await api.writeFile(active.path, contentRef.current, active.version);
      if (res.status === "conflict") {
        contentRef.current = res.content_on_server;
        applyingRemote.current = true;
        setActive((a) => ({ ...a, content: res.content_on_server, version: res.server_version }));
        queueMicrotask(() => {
          applyingRemote.current = false;
        });
        setSaveState("Conflict — reloaded latest version");
        toast({ tone: "error", title: "Save conflict", message: "Reloaded the latest version." });
      } else {
        setActive((a) => ({ ...a, version: res.version }));
        setSaveState(`Saved · v${res.version}`);
        toast({ tone: "success", title: "Saved" });
      }
    } catch (e) {
      toast({ tone: "error", title: "Save failed", message: e.message });
    }
  }

  useEffect(() => {
    function onKey(e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        save();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  // ---- file tree helpers -------------------------------------------------
  const visibleRows = useMemo(() => {
    const rows = [];
    for (const node of tree) {
      const parts = node.path.split("/");
      const depth = parts.length - 1;
      const dirPath = parts.slice(0, -1).join("/");
      if (dirPath && !expandedDirs.has(dirPath)) continue;
      rows.push({ ...node, depth });
    }
    return rows;
  }, [tree, expandedDirs]);

  function toggleDir(path) {
    setExpandedDirs((s) => {
      const n = new Set(s);
      if (n.has(path)) n.delete(path);
      else n.add(path);
      return n;
    });
  }

  async function confirmModalAction() {
    try {
      if (modal === "new" && newFileName.trim()) {
        await api.createNode(newFileName.trim());
        toast({ tone: "success", title: "File created" });
      } else if (modal?.type === "rename" && renameValue.trim()) {
        await api.renameNode(modal.path, renameValue.trim());
        toast({ tone: "success", title: "Renamed" });
      } else if (modal?.type === "delete") {
        await api.deleteNode(modal.path);
        if (activeRef.current?.path === modal.path) {
          setActive(null);
          contentRef.current = "";
        }
        toast({ tone: "success", title: "Deleted" });
      } else if (modal === "end") {
        await api.disconnect();
        toast({ tone: "info", title: "Session ended" });
        onExit();
      }
      refreshTree();
    } catch (e) {
      toast({ tone: "error", title: "Action failed", message: e.message });
    } finally {
      setModal(null);
      setNewFileName("");
      setRenameValue("");
    }
  }

  function copyInvite() {
    navigator.clipboard?.writeText(`IP: ${session.ip}\nCode: ${session.code}`);
    toast({ tone: "success", title: "Invite copied", message: `${session.ip} · ${session.code}` });
  }

  async function decideRequest(requestId, approve) {
    setRequests((r) => r.filter((x) => x.request_id !== requestId));
    try {
      await api.approveGuest(requestId, approve);
      toast(
        approve
          ? { tone: "success", title: "Request approved" }
          : { tone: "info", title: "Request denied" }
      );
    } catch (e) {
      toast({ tone: "error", title: "Action failed", message: e.message });
    }
  }

  async function removeUser(name) {
    try {
      await api.kickUser(name);
      toast({ tone: "info", title: `${name} was removed` });
    } catch (e) {
      toast({ tone: "error", title: "Could not remove user", message: e.message });
    }
  }

  const lineNumbers = useMemo(() => {
    const count = (active?.content || "").split("\n").length;
    return Array.from({ length: Math.max(count, 1) }, (_, i) => i + 1).join("\n");
  }, [active?.content]);

  const presenceList = Object.entries(cursors);

  return (
    <m.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.18 } }}
      className="flex h-full gap-4 p-4"
    >
      <Sidebar
        active={section}
        onSelect={setSection}
        expanded={sidebarExpanded}
        onToggle={() => setSidebarExpanded((v) => !v)}
      />

      {/* main column */}
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        {waitingApproval && (
          <div className="glass flex items-center gap-3 rounded-[18px] border border-accent/30 px-5 py-3">
            <span className="h-2.5 w-2.5 shrink-0 animate-pulse rounded-full bg-[var(--color-accent,#E8B15A)]" />
            <span className="text-sm">
              Waiting for the host to approve your join request…
            </span>
          </div>
        )}
        {/* editor toolbar */}
        <div className="glass flex items-center gap-4 rounded-[18px] px-5 py-3">
          <Icon name="files" size={16} className="text-accent shrink-0" />
          <span className="truncate font-medium">
            {active?.path || "No file selected"}
          </span>
          <span className="text-muted hidden truncate text-xs md:block">{saveState}</span>
          <div className="ml-auto flex items-center gap-4">
            <StatusPill status={wsStatus} />
            <AvatarStack people={peers} />
            <ThemePicker theme={theme} onSelect={onSetTheme} />
          </div>
        </div>

        <div className="flex min-h-0 flex-1 gap-4">
          {/* editor */}
          <div className="glass noise inner-shadow-soft relative flex min-w-0 flex-1 flex-col overflow-hidden rounded-[22px]">
            <div className="flex min-h-0 flex-1">
              <pre
                ref={linesRef}
                className="text-muted select-none overflow-hidden px-4 py-5 text-right font-mono text-sm leading-6 opacity-50"
                style={{ background: "transparent" }}
              >
                {lineNumbers}
              </pre>
              <textarea
                ref={areaRef}
                value={active?.content ?? ""}
                onChange={(e) => {
                  handleInput(e);
                  updateCaret();
                }}
                onKeyUp={updateCaret}
                onClick={updateCaret}
                onScroll={(e) => {
                  if (linesRef.current) linesRef.current.scrollTop = e.target.scrollTop;
                }}
                spellCheck={false}
                disabled={!active}
                placeholder="Open a file to start collaborating…"
                className="editor-area flex-1 overflow-auto py-5 pr-6 font-mono text-sm leading-6"
              />
            </div>

            {/* presence footer */}
            <div className="flex items-center gap-3 border-t border-white/5 px-5 py-2.5 text-xs">
              <span className="text-muted">
                Ln {caret.line}, Col {caret.col}
              </span>
              <div className="ml-auto flex items-center gap-2">
                <AnimatePresence initial={false}>
                  {presenceList.map(([author, c]) =>
                    c.path === active?.path ? (
                      <m.span
                        key={author}
                        layout
                        initial={{ opacity: 0, scale: 0.85 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.85 }}
                        transition={{ type: "spring", stiffness: 380, damping: 28 }}
                        className="glass flex items-center gap-1.5 rounded-full px-2.5 py-1"
                      >
                        <span className="h-2 w-2 rounded-full" style={{ background: c.color }} />
                        {author} · Ln {c.line}
                      </m.span>
                    ) : null
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>

          {/* right panel */}
          <div className="hidden w-[340px] shrink-0 lg:block">
            <AnimatePresence mode="wait">
              <m.div
                key={section}
                initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -8, transition: { duration: 0.15 } }}
                transition={{ type: "spring", stiffness: 280, damping: 28 }}
                className="glass card-shadow h-full overflow-y-auto rounded-[22px] p-6"
              >
                {section === "session" && (
                  <div>
                    <h2 className="font-display text-2xl font-semibold">Hosting Workspace</h2>
                    <p className="text-muted mt-1 text-sm">
                      Share these details with teammates on your Wi-Fi.
                    </p>
                    <div className="mt-6 flex flex-col gap-1">
                      <InfoRow label="Session Code" value={session.code || "—"} onCopy={() => {}} />
                      <InfoRow label="IP Address" value={session.ip || "—"} onCopy={() => {}} />
                      <InfoRow label="Port" value={session.port || "—"} onCopy={() => {}} />
                      <InfoRow label="Users" value={peers.length || 1} onCopy={() => {}} />
                    </div>
                    <div className="mt-6 flex flex-col gap-3">
                      <GlassButton variant="primary" onClick={copyInvite} className="w-full py-3">
                        <Icon name="copy" size={15} /> Copy Invite
                      </GlassButton>
                      <GlassButton variant="danger" onClick={() => setModal("end")} className="w-full py-3">
                        End Session
                      </GlassButton>
                    </div>
                  </div>
                )}

                {section === "files" && (
                  <div>
                    <div className="flex items-center justify-between">
                      <h2 className="font-display text-xl font-semibold">Files</h2>
                      <div className="flex gap-1.5">
                        <button
                          title="New file"
                          onClick={() => setModal("new")}
                          className="text-muted rounded-lg p-2 transition-colors hover:bg-white/10 hover:text-[var(--color-ink)]"
                        >
                          <Icon name="file-plus" size={15} />
                        </button>
                        <button
                          title="Refresh"
                          onClick={refreshTree}
                          className="text-muted rounded-lg p-2 transition-colors hover:bg-white/10 hover:text-[var(--color-ink)]"
                        >
                          <Icon name="settings" size={15} className="rotate-90" />
                        </button>
                      </div>
                    </div>
                    <m.ul variants={listVariants} initial="hidden" animate="show" className="mt-4 flex flex-col gap-0.5">
                      <AnimatePresence initial={false}>
                        {visibleRows.map((node) => (
                          <m.li key={node.path} layout variants={rowVariants} exit={{ opacity: 0, x: -8 }}>
                            <div
                              className={`group flex items-center gap-1 rounded-xl px-2 py-1.5 text-sm transition-colors ${
                                active?.path === node.path ? "glass-bright" : "hover:bg-white/5"
                              }`}
                              style={{ paddingLeft: 8 + node.depth * 14 }}
                            >
                              {node.is_dir ? (
                                <button
                                  onClick={() => toggleDir(node.path)}
                                  className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
                                >
                                  <m.span
                                    animate={{ rotate: expandedDirs.has(node.path) ? 90 : 0 }}
                                    transition={{ duration: 0.18 }}
                                    className="inline-flex"
                                  >
                                    <Icon name="chevron" size={13} />
                                  </m.span>
                                  <span className="truncate">{node.path.split("/").pop()}</span>
                                </button>
                              ) : (
                                <>
                                  <button
                                    onClick={() => openFile(node.path)}
                                    className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
                                  >
                                    <span className="w-[13px]" />
                                    <span className="truncate">{node.path.split("/").pop()}</span>
                                  </button>
                                  <span className="flex opacity-0 transition-opacity group-hover:opacity-100">
                                    <button
                                      title="Rename"
                                      onClick={() => {
                                        setRenameValue(node.path.split("/").pop());
                                        setModal({ type: "rename", path: node.path });
                                      }}
                                      className="text-muted p-1 hover:text-[var(--color-ink)]"
                                    >
                                      <Icon name="pencil" size={12} />
                                    </button>
                                    <button
                                      title="Delete"
                                      onClick={() => setModal({ type: "delete", path: node.path })}
                                      className="text-muted p-1 hover:text-red-300"
                                    >
                                      <Icon name="trash" size={12} />
                                    </button>
                                  </span>
                                </>
                              )}
                            </div>
                          </m.li>
                        ))}
                      </AnimatePresence>
                    </m.ul>
                  </div>
                )}

                {section === "members" && (
                  <div>
                    <h2 className="font-display text-xl font-semibold">Members</h2>

                    {session.role === "host" && requests.length > 0 && (
                      <div className="mt-4">
                        <p className="text-muted text-xs font-medium uppercase tracking-widest">
                          Join requests
                        </p>
                        <m.ul variants={listVariants} initial="hidden" animate="show" className="mt-2 flex flex-col gap-2">
                          {requests.map((req) => (
                            <m.li
                              key={req.request_id}
                              layout
                              variants={rowVariants}
                              className="glass flex items-center gap-3 rounded-2xl border border-accent/30 px-4 py-3"
                            >
                              <span className="min-w-0 flex-1 truncate text-sm">{req.name}</span>
                              <button
                                onClick={() => decideRequest(req.request_id, true)}
                                className="rounded-lg bg-emerald-500/20 px-3 py-1.5 text-xs font-medium text-emerald-300 transition-colors hover:bg-emerald-500/30"
                              >
                                Allow
                              </button>
                              <button
                                onClick={() => decideRequest(req.request_id, false)}
                                className="rounded-lg bg-red-500/20 px-3 py-1.5 text-xs font-medium text-red-300 transition-colors hover:bg-red-500/30"
                              >
                                Deny
                              </button>
                            </m.li>
                          ))}
                        </m.ul>
                      </div>
                    )}

                    <m.ul variants={listVariants} initial="hidden" animate="show" className="mt-5 flex flex-col gap-2">
                      {peers.map((p) => (
                        <m.li
                          key={p.name}
                          layout
                          variants={rowVariants}
                          className="glass flex items-center gap-3 rounded-2xl px-4 py-3"
                        >
                          <span
                            className="flex h-9 w-9 items-center justify-center rounded-full border border-black/30 text-xs font-semibold text-[#14100a]"
                            style={{ background: colorForName(p.name) }}
                          >
                            {(p.name?.[0] || "?").toUpperCase()}
                          </span>
                          <span className="truncate text-sm">{p.name}</span>
                          {p.isHost && (
                            <span className="text-accent ml-auto rounded-full border border-accent/40 px-2 py-0.5 text-[10px] uppercase tracking-wider">
                              Host
                            </span>
                          )}
                          {session.role === "host" && !p.isHost && p.name !== myName && (
                            <button
                              title={`Remove ${p.name}`}
                              onClick={() => removeUser(p.name)}
                              className="text-muted ml-auto rounded-lg p-1.5 transition-colors hover:bg-red-500/20 hover:text-red-300"
                            >
                              <Icon name="trash" size={13} />
                            </button>
                          )}
                        </m.li>
                      ))}
                    </m.ul>
                  </div>
                )}

                {section === "settings" && (
                  <div>
                    <h2 className="font-display text-xl font-semibold">Settings</h2>
                    <div className="mt-6 flex flex-col gap-3">
                      <div className="glass flex items-center justify-between rounded-2xl px-4 py-3.5">
                        <span className="text-sm">Theme</span>
                        <ThemePicker theme={theme} onSelect={onSetTheme} />
                      </div>
                      <div className="glass flex items-center justify-between rounded-2xl px-4 py-3.5">
                        <span className="text-sm">You</span>
                        <span className="text-muted text-sm">{myName}</span>
                      </div>
                      <GlassButton variant="danger" onClick={() => setModal("end")} className="mt-2 w-full py-3">
                        Leave Session
                      </GlassButton>
                    </div>
                  </div>
                )}
              </m.div>
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* modals */}
      <AnimatedModal open={modal === "end"} onClose={() => setModal(null)}>
        <h3 className="font-display text-xl font-semibold">End this session?</h3>
        <p className="text-muted mt-2 text-sm">Everyone connected will be disconnected.</p>
        <div className="mt-7 flex justify-end gap-3">
          <GlassButton variant="secondary" onClick={() => setModal(null)}>
            Cancel
          </GlassButton>
          <GlassButton variant="danger" onClick={confirmModalAction}>
            End Session
          </GlassButton>
        </div>
      </AnimatedModal>

      <AnimatedModal open={modal === "new"} onClose={() => setModal(null)}>
        <h3 className="font-display text-xl font-semibold">New file</h3>
        <GlassInput
          label="File name"
          value={newFileName}
          onChange={(e) => setNewFileName(e.target.value)}
          placeholder="src/main.py"
          className="mt-5"
        />
        <div className="mt-7 flex justify-end gap-3">
          <GlassButton variant="secondary" onClick={() => setModal(null)}>
            Cancel
          </GlassButton>
          <GlassButton variant="primary" onClick={confirmModalAction}>
            Create
          </GlassButton>
        </div>
      </AnimatedModal>

      <AnimatedModal open={!!modal && modal.type === "rename"} onClose={() => setModal(null)}>
        <h3 className="font-display text-xl font-semibold">Rename</h3>
        <GlassInput
          label="New name"
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          className="mt-5"
        />
        <div className="mt-7 flex justify-end gap-3">
          <GlassButton variant="secondary" onClick={() => setModal(null)}>
            Cancel
          </GlassButton>
          <GlassButton variant="primary" onClick={confirmModalAction}>
            Rename
          </GlassButton>
        </div>
      </AnimatedModal>

      <AnimatedModal open={!!modal && modal.type === "delete"} onClose={() => setModal(null)}>
        <h3 className="font-display text-xl font-semibold">Delete file?</h3>
        <p className="text-muted mt-2 text-sm">
          {modal && typeof modal === "object" ? modal.path : ""} will be removed for everyone.
        </p>
        <div className="mt-7 flex justify-end gap-3">
          <GlassButton variant="secondary" onClick={() => setModal(null)}>
            Cancel
          </GlassButton>
          <GlassButton variant="danger" onClick={confirmModalAction}>
            Delete
          </GlassButton>
        </div>
      </AnimatedModal>
    </m.div>
  );
}

// local diff kept here to avoid an extra module boundary in the hot path
function diffLocal(prev, next) {
  let start = 0;
  while (start < prev.length && start < next.length && prev[start] === next[start]) start++;
  let endA = prev.length;
  let endB = next.length;
  while (endA > start && endB > start && prev[endA - 1] === next[endB - 1]) {
    endA--;
    endB--;
  }
  const removed = endA - start;
  const inserted = next.slice(start, endB);
  if (!removed && !inserted.length) return null;
  if (removed && inserted.length)
    return { op: "replace", index: start, length: removed, text: inserted };
  if (inserted.length) return { op: "insert", index: start, text: inserted };
  return { op: "delete", index: start, length: removed };
}
