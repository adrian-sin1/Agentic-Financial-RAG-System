import { useEffect, useRef, useState } from "react";

// Relative, not hardcoded -- the frontend is always served by the same
// FastAPI app it talks to (mounted at /ui), so this automatically resolves
// to whatever host/port/protocol the page itself was loaded from (works on
// any local port, and on the deployed Render domain, with no configuration).
const API_BASE = "";

function SourceList({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <ul className="sources">
      {sources.map((s, i) => (
        <li key={i}>
          {s.company} {s.year} {s.type === "filing" ? `10-K — ${s.detail}` : `— ${s.detail}`}
        </li>
      ))}
    </ul>
  );
}

function Exchange({ entry }) {
  return (
    <div className="exchange">
      <p className="question">{entry.question}</p>
      {entry.loading ? (
        <p className="answer pending">Researching...</p>
      ) : entry.error ? (
        <p className="answer error">{entry.error}</p>
      ) : (
        <>
          <p className="answer">{entry.answer}</p>
          <SourceList sources={entry.sources} />
        </>
      )}
    </div>
  );
}

export default function App() {
  const [entries, setEntries] = useState([]);
  const [input, setInput] = useState("");
  const [apiKey, setApiKey] = useState(() => {
    try {
      return localStorage.getItem("chat_api_key") || "";
    } catch {
      return "";
    }
  });
  const bottomRef = useRef(null);
  const busy = entries.some((e) => e.loading);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  function updateApiKey(value) {
    setApiKey(value);
    try {
      localStorage.setItem("chat_api_key", value);
    } catch {
      /* ignore */
    }
  }

  async function send() {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    const index = entries.length;
    setEntries((prev) => [...prev, { question, loading: true }]);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-api-key": apiKey },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      setEntries((prev) =>
        prev.map((e, i) => (i === index ? { question, answer: data.answer, sources: data.sources } : e))
      );
    } catch (err) {
      setEntries((prev) =>
        prev.map((e, i) => (i === index ? { question, error: err.message || "Something went wrong" } : e))
      );
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter") send();
  }

  return (
    <div className="page">
      <header>
        <h1>Financial Filings Research</h1>
        <p className="subtitle">Grounded Q&amp;A over Apple's FY2025 10-K</p>
      </header>

      <div className="api-key-row">
        <label htmlFor="api-key">API key</label>
        <input
          id="api-key"
          type="password"
          placeholder="CHAT_API_KEY from .env"
          value={apiKey}
          onChange={(e) => updateApiKey(e.target.value)}
        />
      </div>

      <main className="conversation">
        {entries.length === 0 && (
          <p className="empty">Ask something like "What risks does Apple face in its supply chain?"</p>
        )}
        {entries.map((entry, i) => (
          <Exchange entry={entry} key={i} />
        ))}
        <div ref={bottomRef} />
      </main>

      <div className="input-row">
        <input
          type="text"
          placeholder="Ask a question about the filing..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={busy}
        />
        <button onClick={send} disabled={busy}>
          Ask
        </button>
      </div>
    </div>
  );
}
