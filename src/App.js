import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";

// ------------------ VIEW CONFIG ------------------
const VIEW_CONFIG = {
  chat: {
    label: "💬 Chat",
    apiType: null,
  },
  articles: {
    label: "📄 Articles",
    apiType: "article",
  },
  videos: {
    label: "🎥 Videos",
    apiType: "video",
  },
  resources: {
    label: "📚 Resources",
    apiType: "resource",
  },
};

export default function App() {
  const [username, setUsername] = useState("");
  const [loggedIn, setLoggedIn] = useState(false);

  const [view, setView] = useState("chat");

  const [messages, setMessages] = useState([]);
  const [thinking, setThinking] = useState([]);
  const [input, setInput] = useState("");
  const [showThinking, setShowThinking] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const [connected, setConnected] = useState(false);

  const [resources, setResources] = useState([]);
  const [loadingResources, setLoadingResources] = useState(false);

  const wsRef = useRef(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // ------------------ WS ------------------
  useEffect(() => {
    if (!loggedIn || !username) return;

    const ws = new WebSocket(`ws://localhost:5000/ws/${username}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => ws.close();

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.think) {
          setThinking((prev) => [...prev, data.think]);
        }

        if (data.message) {
          setMessages((prev) => [
            ...prev,
            { sender: "server", text: data.message },
          ]);
          setIsTyping(false);
        }
      } catch (e) {
        console.error("WS parse error", e);
      }
    };

    return () => ws.close();
  }, [loggedIn, username]);

  // ------------------ SCROLL ------------------
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // ------------------ FOCUS ------------------
  useEffect(() => {
    if (document.activeElement !== inputRef.current) {
      inputRef.current?.focus();
    }
  }, [input]);

  // ------------------ SEND ------------------
  const sendMessage = () => {
    if (!input.trim()) return;

    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    setThinking([]);
    setIsTyping(true);

    ws.send(JSON.stringify({ message: input }));

    setMessages((prev) => [
      ...prev,
      { sender: "user", text: input },
    ]);

    setInput("");
  };

  // ------------------ FETCH RESOURCES ------------------
  const fetchResources = async () => {
    const apiType = VIEW_CONFIG[view]?.apiType;
    if (!apiType) return;

    setLoadingResources(true);

    try {
      const res = await fetch(
        `http://localhost:5000/get_resource_by_type/${username}/${apiType}`,
        { method: "POST" }
      );

      const data = await res.json();
      setResources(data.response || []);
    } catch (e) {
      console.error("Fetch error", e);
    } finally {
      setLoadingResources(false);
    }
  };

  useEffect(() => {
    if (view !== "chat") {
      fetchResources();
    }
  }, [view]);

  // ------------------ ACTIONS ------------------
  const archiveResource = async (id) => {
    await fetch(
      `http://localhost:5000/update_resource_status/${username}/${id}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "archived" }),
      }
    );

    setResources((prev) => prev.filter((r) => r.id !== id));
  };

  const deleteResource = async (id) => {
    await fetch(
      `http://localhost:5000/delete_resource/${username}/${id}`,
      { method: "DELETE" }
    );

    setResources((prev) => prev.filter((r) => r.id !== id));
  };

  // ------------------ LOGIN ------------------
  if (!loggedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="bg-white p-6 rounded-lg shadow w-[320px] space-y-4">
          <h1 className="text-lg font-semibold text-center">Northstar</h1>

          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter your name"
            className="w-full border px-3 py-2 rounded"
          />

          <button
            onClick={() => username.trim() && setLoggedIn(true)}
            className="w-full bg-black text-white py-2 rounded"
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  // ------------------ SIDEBAR ------------------
  const Sidebar = () => (
    <aside className="w-60 border-r p-4 flex flex-col bg-gray-50">
      <div className="font-semibold mb-6">Northstar</div>

      {Object.entries(VIEW_CONFIG).map(([key, cfg]) => (
        <button
          key={key}
          onClick={() => setView(key)}
          className={`w-full text-left px-3 py-2 rounded mb-2 ${
            view === key ? "bg-gray-200" : "hover:bg-gray-200"
          }`}
        >
          {cfg.label}
        </button>
      ))}
    </aside>
  );

  // ------------------ CHAT ------------------
  const ChatView = () => (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b text-sm">
        {connected ? "🟢 Online" : "🔴 Offline"}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={m.sender === "user" ? "text-right" : ""}>
            <div className="inline-block bg-gray-100 px-3 py-2 rounded">
              {m.sender === "user" ? (
                m.text
              ) : (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                >
                  {m.text}
                </ReactMarkdown>
              )}
            </div>
          </div>
        ))}

        {showThinking && thinking.length > 0 && (
          <div className="text-xs text-gray-500 border-t pt-2">
            {thinking.map((t, i) => (
              <div key={i}>• {t}</div>
            ))}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="p-3 border-t flex gap-2">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 border px-3 py-2 rounded"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              sendMessage();
            }
          }}
        />
        <button
          onClick={sendMessage}
          className="bg-black text-white px-4 rounded"
        >
          Send
        </button>
      </div>
    </div>
  );

  // ------------------ RESOURCE LIST ------------------
  const ContentView = () => (
    <div className="p-6 space-y-3">
      <div className="text-lg font-semibold mb-2">
        {VIEW_CONFIG[view]?.label}
      </div>

      {loadingResources && <div>Loading...</div>}

      {!loadingResources && resources.length === 0 && (
        <div className="text-sm text-gray-400">No items found.</div>
      )}

      {resources.map((r, i) => {
  const id = r.id || r._id || r.resource_id || i;
  const url = r.url || r.link || "#";

  return (
    <div
      key={id}
      className="border p-4 rounded relative hover:bg-gray-50 group"
    >
      {/* CLICKABLE TITLE */}
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium text-blue-600 hover:underline block"
      >
        {r.title || "Untitled"}
      </a>

      {/* CHANNEL / SOURCE */}
      {r.channel && (
        <div className="text-xs text-gray-500 mt-1">
          {r.channel}
        </div>
      )}

      {/* DESCRIPTION (if exists) */}
      {r.description && (
        <div className="text-sm text-gray-500 mt-1">
          {r.description}
        </div>
      )}

      {/* TAGS */}
      {r.tags?.length > 0 && (
        <div className="flex gap-2 mt-2 flex-wrap">
          {r.tags.map((tag, idx) => (
            <span
              key={idx}
              className="text-xs px-2 py-1 bg-gray-200 rounded"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* HOVER ACTIONS (PER ITEM) */}
      <div className="absolute right-3 top-3 hidden group-hover:flex gap-2">
        <button
          onClick={() => archiveResource(id)}
          className="text-xs px-2 py-1 border rounded"
        >
          Archive
        </button>

        <button
          onClick={() => deleteResource(id)}
          className="text-xs px-2 py-1 border rounded text-red-600"
        >
          Delete
        </button>
      </div>
    </div>
  );
})}
    </div>
  );

  // ------------------ MAIN ------------------
  return (
    <div className="h-screen flex">
      <Sidebar />

      <div className="flex-1">
        {view === "chat" ? <ChatView /> : <ContentView />}
      </div>
    </div>
  );
}