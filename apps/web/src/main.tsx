import { FormEvent, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Message = { id: string; role: "child" | "assistant"; content: string; time: string; state?: "safe" | "guided"; source?: "local" | "llm" };
type Conversation = { id: string; title: string; topic: string; updated: string; messages: Message[] };
type LlmStatus = { available: boolean; enabledDefault: boolean; model?: string; mode: string };

const welcome: Message = { id: "welcome", role: "assistant", content: "Hi Maya! I’m here to help you learn. What would you like to explore today?", time: "Now", state: "safe" };
const starterConversations: Conversation[] = [
  { id: "space", title: "Why do stars twinkle?", topic: "Space", updated: "Today", messages: [welcome, { id: "s1", role: "child", content: "Why do stars twinkle?", time: "3:12 PM" }, { id: "s2", role: "assistant", content: "Stars seem to twinkle because we look at them through moving layers of air around Earth. The air bends their light a tiny bit in changing directions. Planets look steadier because they appear bigger in our sky.", time: "3:12 PM", state: "safe" }] },
  { id: "plants", title: "How plants drink water", topic: "Science", updated: "Yesterday", messages: [welcome, { id: "p1", role: "child", content: "How do plants drink water?", time: "Yesterday" }, { id: "p2", role: "assistant", content: "Roots soak up water from the soil. Then tiny tubes inside the plant carry it up to the leaves, a bit like a very small straw system.", time: "Yesterday", state: "safe" }] },
  { id: "fractions", title: "Fraction practice", topic: "Maths", updated: "Monday", messages: [welcome, { id: "f1", role: "child", content: "Can you help me understand halves?", time: "Monday" }, { id: "f2", role: "assistant", content: "A half means one of two equal parts. If you split a sandwich into two equal pieces, each piece is one half.", time: "Monday", state: "safe" }] }
];

const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const useLlmStorageKey = "brightpath.useLlm";

function App() {
  const [conversations, setConversations] = useState(starterConversations);
  const [activeId, setActiveId] = useState("space");
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [llm, setLlm] = useState<LlmStatus>({ available: false, enabledDefault: false, mode: "safe-local-demo" });
  const [useLlm, setUseLlm] = useState(false);
  const active = conversations.find((conversation) => conversation.id === activeId) ?? conversations[0];
  const filtered = useMemo(() => conversations.filter((conversation) => `${conversation.title} ${conversation.topic}`.toLowerCase().includes(query.toLowerCase())), [conversations, query]);

  useEffect(() => {
    fetch(`${apiBase}/health`)
      .then((response) => response.json())
      .then((data) => {
        const available = Boolean(data.llm_available);
        const enabledDefault = Boolean(data.llm_enabled_default);
        setLlm({ available, enabledDefault, model: data.model || undefined, mode: data.mode });
        const stored = localStorage.getItem(useLlmStorageKey);
        if (stored !== null) setUseLlm(stored === "true" && available);
        else setUseLlm(available && enabledDefault);
      })
      .catch(() => undefined);
  }, []);

  function updateUseLlm(next: boolean) {
    const enabled = next && llm.available;
    setUseLlm(enabled);
    localStorage.setItem(useLlmStorageKey, String(enabled));
  }

  function startConversation() {
    const id = crypto.randomUUID();
    setConversations((items) => [{ id, title: "New question", topic: "Learning", updated: "Now", messages: [welcome] }, ...items]);
    setActiveId(id); setDraft("");
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || waiting) return;
    const childMessage: Message = { id: crypto.randomUUID(), role: "child", content, time: "Now" };
    setConversations((items) => items.map((conversation) => conversation.id === active.id ? { ...conversation, title: conversation.title === "New question" ? content.slice(0, 42) : conversation.title, updated: "Now", messages: [...conversation.messages, childMessage] } : conversation));
    setDraft(""); setWaiting(true);
    try {
      const response = await fetch(`${apiBase}/v1/chat/messages`, { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": childMessage.id }, body: JSON.stringify({ conversation_id: active.id, content, use_llm: useLlm }) });
      if (!response.ok) throw new Error("Safe answer unavailable");
      const data = await response.json();
      const assistantMessage: Message = { id: data.id, role: "assistant", content: data.content, time: "Now", state: data.safety_state, source: data.source };
      setConversations((items) => items.map((conversation) => conversation.id === active.id ? { ...conversation, topic: data.topic || conversation.topic, messages: [...conversation.messages, assistantMessage] } : conversation));
    } catch {
      const fallback: Message = { id: crypto.randomUUID(), role: "assistant", content: "I need a moment before I can answer safely. Please try again soon, or ask a trusted adult to help.", time: "Now", state: "guided" };
      setConversations((items) => items.map((conversation) => conversation.id === active.id ? { ...conversation, messages: [...conversation.messages, fallback] } : conversation));
    } finally { setWaiting(false); }
  }

  return <main className="app-shell">
    <aside className="sidebar"><div className="brand"><span className="brand-mark">✦</span><span>BrightPath</span></div><button className="new-chat" onClick={startConversation}>＋ New chat</button><label className="search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search your chats" /></label><p className="side-label">YOUR LEARNING</p><nav>{filtered.map((conversation) => <button key={conversation.id} onClick={() => setActiveId(conversation.id)} className={`conversation-link ${activeId === conversation.id ? "selected" : ""}`}><span className="conversation-title">{conversation.title}</span><span>{conversation.topic} · {conversation.updated}</span></button>)}</nav><div className="sidebar-footer"><button className="profile">M <span>Maya’s profile</span><span>⌄</span></button><button className="admin-link" onClick={() => setAdminOpen(true)}>Guardian settings</button></div></aside>
    <section className="chat"><header className="topbar"><div><p className="eyebrow">MAYA’S LEARNING SPACE</p><h1>{active.title}</h1></div><div className="topbar-actions"><label className="llm-toggle" title={llm.available ? "Send this question to the configured LLM" : "Add OPENAI_API_KEY in apps/api/.env to enable AI answers"}><input type="checkbox" checked={useLlm} disabled={!llm.available || waiting} onChange={(event) => updateUseLlm(event.target.checked)} /><span>{useLlm ? "AI answers on" : "AI answers off"}</span></label><div className="safety-badge"><span>✓</span> Safe learning space</div></div></header><div className="messages">{active.messages.map((message) => <article key={message.id} className={`message ${message.role}`}><div className="avatar">{message.role === "child" ? "M" : "✦"}</div><div><div className="bubble">{message.content}</div><div className="message-meta">{message.time}{message.role === "assistant" && <span className="checked"> · Checked for safety</span>}{message.source === "llm" && <span className="source-llm"> · AI answer</span>}</div></div></article>)}{waiting && <article className="message assistant"><div className="avatar">✦</div><div><div className="bubble thinking"><i></i><i></i><i></i></div><div className="message-meta">Checking this answer is safe…</div></div></article>}</div><form className="composer" onSubmit={send}><textarea value={draft} maxLength={1200} onChange={(event) => setDraft(event.target.value)} placeholder="Ask anything you’re curious about…" aria-label="Your question" /><button disabled={!draft.trim() || waiting}>{waiting ? "Checking…" : "Ask"}</button><p>Be kind, curious, and don’t share personal details like your address or passwords.</p></form></section>
    {adminOpen && <Admin onClose={() => setAdminOpen(false)} llm={llm} useLlm={useLlm} onUseLlm={updateUseLlm} />}
  </main>;
}

function Admin({ onClose, llm, useLlm, onUseLlm }: { onClose: () => void; llm: LlmStatus; useLlm: boolean; onUseLlm: (next: boolean) => void }) {
  const [tab, setTab] = useState("Overview");
  return <div className="modal-backdrop"><section className="admin-panel"><header><div><p className="eyebrow">GUARDIAN AREA · DEMO</p><h2>Learning safety</h2></div><button className="icon-button" onClick={onClose}>×</button></header><div className="admin-layout"><nav>{["Overview", "Safety profile", "Knowledge review", "Topics", "Activity"].map((item) => <button className={tab === item ? "active" : ""} onClick={() => setTab(item)} key={item}>{item}</button>)}</nav><div className="admin-content">
    {tab === "Overview" ? <>
      <h3>AI answers</h3>
      <p className="muted">Keys stay in <code>apps/api/.env</code>. The browser never receives the provider key.</p>
      <div className="profile-card">
        <div><span className="card-label">STATUS</span><strong>{llm.available ? "LLM configured" : "Local demo only"}</strong></div>
        <div><span className="card-label">MODEL</span><strong>{llm.model || "Not set"}</strong></div>
        <div><span className="card-label">DEFAULT</span><strong>{llm.enabledDefault ? "On from .env" : "Off until you choose it"}</strong></div>
      </div>
      <label className="llm-toggle admin-toggle" title={llm.available ? "Use the LLM for learning questions" : "Add OPENAI_API_KEY in apps/api/.env, then restart the API"}>
        <input type="checkbox" checked={useLlm} disabled={!llm.available} onChange={(event) => onUseLlm(event.target.checked)} />
        <span>Send learning questions to the LLM</span>
      </label>
      <p className="muted">Set <code>OPENAI_API_KEY</code> and optionally <code>LLM_ENABLED=true</code> in <code>apps/api/.env</code>, then restart the API. Help-seeking and harmful requests still never reach the model.</p>
    </> : tab === "Safety profile" ? <><h3>Maya’s safety profile</h3><p className="muted">Active profile: <strong>Ages 8–10 · Version 3</strong></p><div className="profile-card"><div><span className="card-label">READING STYLE</span><strong>Clear, friendly · short answers</strong></div><div><span className="card-label">LANGUAGE</span><strong>English</strong></div><div><span className="card-label">OUTPUT CHECK</span><strong>Required before display</strong></div></div><h3>Moderation thresholds</h3><p className="muted">Thresholds are server-enforced and versioned. Scores are never shown to children.</p><table><thead><tr><th>Category</th><th>Input</th><th>Output</th><th>Action</th></tr></thead><tbody>{[["Violence", "Guide at 0.15", "Block at 0.65", "Guided answer"],["Self-harm", "Support routing", "Support routing", "Trusted adult"],["Sexual content", "Guide at 0.10", "Block at 0.45", "Age-appropriate"],["Harassment", "Guide at 0.20", "Block at 0.60", "Kind redirection"]].map((row) => <tr key={row[0]}>{row.map((cell) => <td key={cell}>{cell}</td>)}</tr>)}</tbody></table><button className="publish">Create new draft</button></> : <><h3>{tab}</h3><p className="muted">This area is ready to connect to the protected FastAPI admin endpoints and Supabase role checks.</p></>}
  </div></div></section></div>;
}

createRoot(document.getElementById("root")!).render(<App />);
