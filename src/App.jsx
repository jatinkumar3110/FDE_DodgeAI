import React, { useEffect, useRef, useState } from "react";
import "./styles.css";

const API_URL = "https://YOUR_RENDER_URL/query";

function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: "system",
      text: "Ask an ERP query, for example: Find journal for invoice 91150187",
    },
  ]);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    const userText = query.trim();
    if (!userText || loading) {
      return;
    }

    const userMessage = {
      id: Date.now(),
      role: "user",
      text: userText,
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setLoading(true);

    const start = performance.now();

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: userText }),
      });

      if (!response.ok) {
        throw new Error("Request failed");
      }

      const data = await response.json();
      const elapsedMs = Math.round(performance.now() - start);

      const systemMessage = {
        id: Date.now() + 1,
        role: "system",
        text: data?.answer || "No response",
        parsedQuery: data?.parsed_query,
        executionMs: data?.result?.execution_ms || elapsedMs,
      };

      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 2,
          role: "system",
          text: "Error fetching response",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <div className="chat-shell">
        <header className="chat-header">ERP Query Chat</header>

        <div className="chat-history">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message-row ${message.role === "user" ? "user" : "system"}`}
            >
              <div className="message-bubble">
                <div className="message-role">{message.role === "user" ? "User" : "System"}</div>
                <div className="message-text">{message.text}</div>

                {message.role === "system" && message.parsedQuery && (
                  <details className="meta-box">
                    <summary>Parsed query</summary>
                    <pre>{JSON.stringify(message.parsedQuery, null, 2)}</pre>
                  </details>
                )}

                {message.role === "system" && message.executionMs ? (
                  <div className="meta-time">{message.executionMs} ms</div>
                ) : null}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message-row system">
              <div className="message-bubble">
                <div className="message-role">System</div>
                <div className="message-text">Loading...</div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <form className="chat-input-area" onSubmit={handleSubmit}>
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Type your ERP query..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? "Sending..." : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
