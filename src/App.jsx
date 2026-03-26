import React, { Component, Suspense, lazy, useEffect, useRef, useState } from "react";
import "./styles.css";

const QUERY_API_URL = "https://fde-dodgeai.onrender.com/query";
const GRAPH_API_URL = "https://fde-dodgeai.onrender.com/graph";
const LazyGraphView = lazy(() => import("./GraphView"));

const readLastQuery = () => {
  try {
    return localStorage.getItem("erp_last_query") || "";
  } catch (error) {
    console.warn("Unable to read last query from localStorage", error);
    return "";
  }
};

class GraphErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error("GraphView crash:", error);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [queryError, setQueryError] = useState("");
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loadingGraph, setLoadingGraph] = useState(true);
  const [highlightNodeIds, setHighlightNodeIds] = useState([]);
  const [lastQuery, setLastQuery] = useState(readLastQuery);
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

  useEffect(() => {
    const loadGraph = async () => {
      setLoadingGraph(true);
      try {
        console.log("Fetching graph...");
        const res = await fetch(GRAPH_API_URL);
        if (!res.ok) {
          throw new Error("Graph request failed");
        }
        const data = await res.json();
        console.log("Graph API response:", data);
        setGraphData({
          nodes: data?.nodes || [],
          links: data?.links || [],
        });
      } catch (err) {
        console.error("Graph fetch error:", err);
        setGraphData({ nodes: [], links: [] });
      } finally {
        setLoadingGraph(false);
      }
    };

    loadGraph();
  }, []);

  useEffect(() => {
    console.log("Graph Data:", graphData);
  }, [graphData]);

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

    try {
      localStorage.setItem("erp_last_query", userText);
    } catch (error) {
      console.warn("Unable to persist last query", error);
    }
    setLastQuery(userText);

    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setQueryError("");
    setLoading(true);

    const start = performance.now();

    try {
      const response = await fetch(QUERY_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: userText }),
      });

      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }

      const data = await response.json();
      const elapsedMs = Math.round(performance.now() - start);

      const systemMessage = {
        id: Date.now() + 1,
        role: "system",
        text: data?.answer || "No response",
        parsedQuery: data?.parsed_query,
        result: data?.result,
        queryPlan: data?.query_plan || data?.result?.data?.query_plan,
        executionMs: data?.execution_time_ms || elapsedMs,
      };

      setHighlightNodeIds(data?.highlight_nodes || data?.result?.data?.highlight_nodes || []);

      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      setHighlightNodeIds([]);
      setQueryError(error?.message || "Unable to process your request right now.");
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 2,
          role: "system",
          text: `Unable to process your request right now. ${error?.message || "Please try again."}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const renderGraphPanel = () => {
    if (loadingGraph) {
      return (
        <section className="graph-shell">
          <div className="graph-state">Loading graph...</div>
        </section>
      );
    }

    if (!graphData || graphData.nodes.length === 0) {
      return (
        <section className="graph-shell">
          <div className="graph-state">Graph not available</div>
        </section>
      );
    }

    try {
      return (
        <GraphErrorBoundary
          fallback={
            <section className="graph-shell">
              <div className="graph-state">Graph failed to render</div>
            </section>
          }
        >
          <Suspense
            fallback={
              <section className="graph-shell">
                <div className="graph-state">Loading graph...</div>
              </section>
            }
          >
            <LazyGraphView graphData={graphData} highlightedNodeIds={highlightNodeIds} />
          </Suspense>
        </GraphErrorBoundary>
      );
    } catch (error) {
      console.error("GraphView crash:", error);
      return (
        <section className="graph-shell">
          <div className="graph-state">Graph failed to render</div>
        </section>
      );
    }
  };

  return (
    <div className="app">
      <div className="layout-shell" style={{ gridTemplateColumns: "1.86fr 1fr" }}>
        {renderGraphPanel()}

        <div className="chat-shell">
          <header className="chat-header">ERP Query Chat</header>

          {lastQuery ? <div className="chat-last-query">Last query: {lastQuery}</div> : null}

          {queryError ? (
            <div className="chat-last-query" style={{ color: "#b91c1c", background: "#fff1f2" }}>
              Error: {queryError}
            </div>
          ) : null}

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

                  {message.role === "system" && message.queryPlan && (
                    <details className="meta-box">
                      <summary>Query Plan</summary>
                      <pre>{JSON.stringify(message.queryPlan, null, 2)}</pre>
                    </details>
                  )}

                  {message.role === "system" && message.result && (
                    <details className="meta-box">
                      <summary>Structured result</summary>
                      {message.result?.data?.flow_path ? (
                        <div className="meta-time">Flow: {message.result.data.flow_path}</div>
                      ) : null}
                      {message.result?.data?.order_count !== undefined ||
                      message.result?.data?.delivery_count !== undefined ||
                      message.result?.data?.invoice_count !== undefined ||
                      message.result?.data?.journal_count !== undefined ||
                      message.result?.data?.payment_count !== undefined ? (
                        <div className="meta-time">
                          Counts: order={message.result?.data?.order_count ?? 0}, delivery=
                          {message.result?.data?.delivery_count ?? 0}, invoice=
                          {message.result?.data?.invoice_count ?? 0}, journal=
                          {message.result?.data?.journal_count ?? 0}, payment=
                          {message.result?.data?.payment_count ?? 0}
                        </div>
                      ) : null}
                      <pre>{JSON.stringify(message.result, null, 2)}</pre>
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
                  <div className="message-text">Processing query...</div>
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
    </div>
  );
}

export default App;
