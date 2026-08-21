const BASE = import.meta.env.DEV ? "http://127.0.0.1:7432" : "";

async function post(path, body) {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || "Request failed");
  return data;
}

export const api = {
  hostSession: (name, filepath) => post("/host", { name, filepath }),
  pickFolder: () => post("/dialog/folder", {}),
  validateGuest: (host_ip, code) => post("/guest/validate", { host_ip, code }),
  connectGuest: (name, host_ip, code) => post("/guest/connect", { name, host_ip, code }),
  projectTree: () => post("/project/tree", {}),
  readFile: (path) => post("/file/read", { path }),
  writeFile: (path, content, version) => post("/file/write", { path, content, version }),
  createNode: (path, is_dir = false) => post("/file/create", { path, is_dir }),
  renameNode: (path, new_name) => post("/file/rename", { path, new_name }),
  deleteNode: (path) => post("/file/delete", { path }),
  setActiveFile: (path) => post("/file/active", { path }),
  textEdit: (path, op) => post("/text/edit", { path, op }),
  cursor: (path, line, col) => post("/cursor", { path, line, col }),
  disconnect: () => post("/disconnect", {}),
  peers: async () => {
    const res = await fetch(BASE + "/peers");
    return res.json();
  },
};

let socket = null;

export function connectWS(onEvent, onStatus) {
  if (socket) socket.close();
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const url = import.meta.env.DEV ? `ws://127.0.0.1:7432/ws` : `${proto}://${location.host}/ws`;
  const ws = new WebSocket(url);
  socket = ws;
  ws.onopen = () => onStatus?.("connected");
  ws.onclose = () => {
    if (socket === ws) {
      socket = null;
      onStatus?.("offline");
    }
  };
  ws.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data));
    } catch {
      /* ignore malformed frames */
    }
    return undefined;
  };
  return () => {
    if (socket === ws) {
      socket = null;
      ws.close();
    }
  };
}

export function diffOp(prev, next) {
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

export function applyOp(text, op) {
  const i = Math.max(0, Math.min(op.index ?? 0, text.length));
  if (op.op === "insert") return text.slice(0, i) + (op.text || "") + text.slice(i);
  if (op.op === "delete") return text.slice(0, i) + text.slice(i + (op.length || 0));
  if (op.op === "replace")
    return text.slice(0, i) + (op.text || "") + text.slice(i + (op.length || 0));
  return text;
}
